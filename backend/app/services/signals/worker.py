import asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.logging import get_logger, configure_logging
from app.db.session import async_session_factory
from app.models.ingestion import Channel
from app.models.news import News, NewsSource
from app.models.trading import PaperTrade, SignalRow
from app.services.ingestion.queue import (
    ANALYZED_STREAM,
    CONSUMER_GROUP,
    close,
    ensure_groups,
    get_client,
    publish_dlq,
    publish_signal,
)
from app.schemas.signal import SignalStatus
from app.services.signals.engine import TIMEFRAME_CANDLE, build_signal
from app.services.trading import risk as risk_module
from app.services.trading import paper

log = get_logger("signals.worker")

CONSUMER = "signaler-1"


async def _independent_origins(session, news_id: int) -> int:
    value = await session.scalar(
        select(func.count(func.distinct(NewsSource.channel_id))).where(
            NewsSource.news_id == news_id,
            NewsSource.is_origin.is_(True),
        )
    )
    return int(value or 0)


async def _credibility(session, channel_id) -> float:
    if channel_id is None:
        return 0.5
    channel = await session.get(Channel, channel_id)
    if channel is None or channel.credibility is None:
        return 0.5
    return float(channel.credibility)


async def _open_positions(session) -> int:
    value = await session.scalar(
        select(func.count()).select_from(PaperTrade).where(PaperTrade.closed_at.is_(None))
    )
    return int(value or 0)


async def _open_risk_amount(session, equity: float) -> float:
    result = await session.execute(
        select(SignalRow.risk_pct)
        .join(PaperTrade, PaperTrade.signal_id == SignalRow.id)
        .where(PaperTrade.closed_at.is_(None))
    )
    total = sum(float(row[0] or 0.0) for row in result.all())
    return total * equity


async def _realized_pnl_pct(session, equity: float, since) -> float:
    total = await session.scalar(
        select(func.coalesce(func.sum(PaperTrade.pnl), 0)).where(
            PaperTrade.closed_at.is_not(None),
            PaperTrade.closed_at >= since,
        )
    )
    if not equity:
        return 0.0
    return float(total or 0.0) / equity * 100.0


async def _fetch_candles(asset: str, timeframe: str) -> list[dict]:
    from app.services.trading import exchanges

    try:
        exchange = exchanges.build_exchange(
            settings.default_exchange, "", "", testnet=False
        )
        try:
            return await exchanges.fetch_candles(exchange, asset, timeframe)
        finally:
            await exchange.close()
    except Exception as exc:
        log.error("candle fetch failed: %s" % exc, extra={"stage": "signals"})
        return []


async def process(payload: dict) -> None:
    news_id = payload["news_id"]
    async with async_session_factory() as session:
        news = await session.get(News, news_id)
        if news is None or news.analysis_status != "analyzed":
            return
        if not news.asset_resolved or not news.coins:
            return

        framework = TIMEFRAME_CANDLE.get(news.impact_timeframe or "intraday", "15m")
        asset = f"{news.coins[0]}/USDT"
        candles = await _fetch_candles(asset, framework)

        price = (payload.get("enrichment") or {}).get("price")
        if price is None:
            from app.services.analysis import market

            try:
                price = await market.fetch_price(news.coins[0])
            except Exception:
                price = None
        if price is None:
            return

        independent_origins = await _independent_origins(session, news_id)
        credibility = await _credibility(session, news.origin_channel_id)

        signal, reason = build_signal(
            news_id=news_id,
            asset=asset,
            event_type=news.event_type or "other",
            sentiment=news.sentiment or "neutral",
            sentiment_score=float(news.sentiment_score or 0.0),
            certainty=float(news.certainty or 0.0),
            source_credibility=credibility,
            independent_origins=independent_origins,
            price=float(price),
            candles=candles,
            impact_timeframe=news.impact_timeframe or "intraday",
            prompt_version=news.prompt_version or "",
        )
        if signal is None:
            log.info(
                "no signal for news %s: %s" % (news_id, reason),
                extra={"stage": "signals"},
            )
            return

        equity = settings.paper_equity
        now = datetime.now(timezone.utc)
        open_risk = await _open_risk_amount(session, equity)
        state = risk_module.RiskState(
            equity=equity,
            open_positions=await _open_positions(session),
            open_risk_amount=open_risk,
            correlated_risk_amount=open_risk,
            daily_pnl_pct=await _realized_pnl_pct(
                session, equity, now - timedelta(days=1)
            ),
            weekly_pnl_pct=await _realized_pnl_pct(
                session, equity, now - timedelta(days=7)
            ),
            kill_switch=settings.kill_switch,
        )
        decision = risk_module.evaluate(
            signal,
            risk_module.RiskConfig(),
            state,
            market_risk_factor=signal.market_risk_factor,
            spread_pct=0.0,
            depth_ok=True,
            beta_to_btc=1.0,
        )

        if not decision.approved:
            signal.status = SignalStatus.rejected
            await _persist_signal(session, signal, decision.reasons)
            await session.commit()
            await publish_signal(
                {
                    "signal_id": signal.signal_id,
                    "status": signal.status.value,
                    "reasons": decision.reasons,
                }
            )
            return

        signal.risk_pct = decision.risk_pct
        signal.status = SignalStatus.active
        await _persist_signal(session, signal, [])

        if settings.trading_mode == "paper":
            fill = paper.simulate_entry(
                signal_id=signal.signal_id,
                asset=signal.asset,
                direction=signal.direction,
                entry_price=signal.entry_low,
                quantity=decision.size,
            )
            session.add(
                PaperTrade(
                    signal_id=signal.signal_id,
                    asset=signal.asset,
                    direction=signal.direction.value,
                    entry_price=Decimal(str(fill["entry_price"])),
                    quantity=Decimal(str(fill["quantity"])),
                    fees=Decimal(str(fill["fees"])),
                    opened_at=signal.created_at,
                )
            )

        await session.commit()

        await publish_signal(
            {
                "signal_id": signal.signal_id,
                "news_id": signal.news_id,
                "asset": signal.asset,
                "direction": signal.direction.value,
                "entry_low": signal.entry_low,
                "entry_high": signal.entry_high,
                "stop_loss": signal.stop_loss,
                "take_profits": signal.take_profits,
                "confidence": signal.confidence,
                "market_risk_factor": signal.market_risk_factor,
                "risk_pct": signal.risk_pct,
                "size": decision.size,
                "status": signal.status.value,
                "risk_reward": signal.risk_reward,
                "expires_at": signal.expires_at.isoformat(),
            }
        )


async def _persist_signal(session, signal, reasons: list[str]) -> None:
    values = {
        "id": signal.signal_id,
        "news_id": signal.news_id,
        "asset": signal.asset,
        "direction": signal.direction.value,
        "entry_low": Decimal(str(signal.entry_low)),
        "entry_high": Decimal(str(signal.entry_high)),
        "order_type": signal.order_type,
        "stop_loss": Decimal(str(signal.stop_loss)),
        "take_profits": [Decimal(str(tp)) for tp in signal.take_profits],
        "leverage_suggested": signal.leverage_suggested,
        "timeframe": signal.timeframe,
        "confidence": signal.confidence,
        "market_risk_factor": Decimal(str(round(signal.market_risk_factor, 3))),
        "risk_pct": Decimal(str(round(signal.risk_pct, 4))),
        "rationale": signal.rationale + (" | " + ",".join(reasons) if reasons else ""),
        "risk_reward": Decimal(str(round(signal.risk_reward, 2))),
        "status": signal.status.value,
        "prompt_version": signal.prompt_version,
        "expires_at": signal.expires_at,
    }
    statement = pg_insert(SignalRow).values(**values)
    update_columns = {
        key: statement.excluded[key]
        for key in values
        if key not in ("id", "news_id", "created_at")
    }
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[SignalRow.id], set_=update_columns
        )
    )


async def run() -> None:
    configure_logging(settings.log_level)
    await ensure_groups()
    client = get_client()
    log.info("signals worker started", extra={"stage": "signals"})

    while True:
        try:
            response = await client.xreadgroup(
                CONSUMER_GROUP,
                CONSUMER,
                {ANALYZED_STREAM: ">"},
                count=10,
                block=5000,
            )
        except Exception as exc:
            log.error("read failed: %s" % exc, extra={"stage": "signals"})
            await asyncio.sleep(1)
            continue

        if not response:
            continue

        for _stream, entries in response:
            for entry_id, fields in entries:
                payload = json.loads(fields["payload"])
                try:
                    await process(payload)
                except Exception as exc:
                    log.error("signals failed: %s" % exc, extra={"stage": "signals"})
                    await publish_dlq(payload, str(exc))
                finally:
                    await client.xack(ANALYZED_STREAM, CONSUMER_GROUP, entry_id)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        asyncio.run(close())
