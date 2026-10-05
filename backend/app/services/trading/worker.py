import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory
from app.models.trading import PaperTrade, SignalRow
from app.schemas.signal import Direction, SignalStatus
from app.services.ingestion.queue import close, publish_signal
from app.services.trading import manage

log = get_logger("trading.worker")

POLL_SECONDS = 30


async def _latest_candle(asset: str, timeframe: str) -> dict | None:
    from app.services.trading import exchanges

    try:
        exchange = exchanges.build_exchange(
            settings.default_exchange, "", "", testnet=False
        )
        try:
            candles = await exchanges.fetch_candles(exchange, asset, timeframe, limit=5)
        finally:
            await exchange.close()
    except Exception as exc:
        log.error("candle fetch failed: %s" % exc, extra={"stage": "executor"})
        return None
    return candles[-1] if candles else None


async def process_open_trades() -> int:
    now = datetime.now(timezone.utc)
    closed = 0
    async with async_session_factory() as session:
        result = await session.execute(
            select(PaperTrade, SignalRow)
            .join(SignalRow, PaperTrade.signal_id == SignalRow.id)
            .where(PaperTrade.closed_at.is_(None))
        )
        rows = result.all()
        if not rows:
            return 0

        cache: dict[tuple[str, str], dict | None] = {}
        for trade, signal in rows:
            key = (signal.asset, signal.timeframe)
            if key not in cache:
                cache[key] = await _latest_candle(signal.asset, signal.timeframe)
            candle = cache[key]
            if candle is None:
                continue

            decision = manage.evaluate_exit(
                direction=Direction(trade.direction),
                entry_price=float(trade.entry_price),
                quantity=float(trade.quantity),
                fees=float(trade.fees or 0.0),
                stop_loss=float(signal.stop_loss),
                take_profit=float(signal.take_profits[0]),
                candle=candle,
                now=now,
                expires_at=signal.expires_at,
            )
            if decision is None:
                continue

            trade.exit_price = Decimal(str(round(decision.exit_price, 8)))
            trade.pnl = Decimal(str(round(decision.pnl, 8)))
            trade.pnl_pct = Decimal(str(round(decision.pnl_pct, 6)))
            trade.closed_at = now
            trade.close_reason = decision.reason
            signal.status = SignalStatus.closed.value
            closed += 1

            await publish_signal(
                {
                    "signal_id": signal.id,
                    "asset": signal.asset,
                    "status": SignalStatus.closed.value,
                    "close_reason": decision.reason,
                    "pnl": decision.pnl,
                    "pnl_pct": decision.pnl_pct,
                }
            )

        await session.commit()
    return closed


async def run() -> None:
    configure_logging(settings.log_level)
    log.info("executor worker started", extra={"stage": "executor"})
    while True:
        try:
            closed = await process_open_trades()
            if closed:
                log.info(
                    "closed %s paper trades" % closed, extra={"stage": "executor"}
                )
        except Exception as exc:
            log.error("executor failed: %s" % exc, extra={"stage": "executor"})
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        asyncio.run(close())
