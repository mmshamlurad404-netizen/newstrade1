import json
from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import serializers
from app.api.deps import require_token, verify_token
from app.core import runtime
from app.core.config import settings
from app.db.session import get_session
from app.models.ingestion import Channel
from app.models.news import News, NewsSource, RawMessage
from app.models.trading import PaperTrade, SignalRow, Trade
from app.schemas.api import KillSwitchUpdate
from app.services.ingestion.queue import (
    FAST_ALERTS_STREAM,
    SIGNALS_STREAM,
    get_client,
)

router = APIRouter(prefix="/api", dependencies=[Depends(require_token)])
ws_router = APIRouter()


async def _channel_titles(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    channels = (
        await session.scalars(select(Channel).where(Channel.id.in_(ids)))
    ).all()
    return {channel.id: channel.title for channel in channels}


@router.get("/news")
async def list_news(
    coin: str | None = None,
    event_type: str | None = None,
    urgency: str | None = None,
    channel_id: int | None = None,
    since: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    statement = select(News).order_by(News.first_seen_at.desc()).limit(limit)
    if coin:
        statement = statement.where(News.coins.any(coin.upper()))
    if event_type:
        statement = statement.where(News.event_type == event_type)
    if urgency:
        statement = statement.where(News.urgency == urgency)
    if channel_id:
        statement = statement.where(News.origin_channel_id == channel_id)
    if since:
        statement = statement.where(News.first_seen_at >= since)
    rows = (await session.scalars(statement)).all()
    titles = await _channel_titles(
        session, {row.origin_channel_id for row in rows if row.origin_channel_id}
    )
    return [
        serializers.serialize_news(row, titles.get(row.origin_channel_id))
        for row in rows
    ]


@router.get("/news/{news_id}")
async def get_news(
    news_id: int, session: AsyncSession = Depends(get_session)
) -> dict:
    news = await session.get(News, news_id)
    if news is None:
        raise HTTPException(status_code=404, detail="news not found")

    result = await session.execute(
        select(RawMessage, Channel, NewsSource)
        .join(Channel, RawMessage.channel_id == Channel.id)
        .join(NewsSource, NewsSource.raw_message_id == RawMessage.id)
        .where(NewsSource.news_id == news_id)
    )
    sources = []
    for message, channel, source in result.all():
        sources.append(
            {
                "channel": channel.title,
                "channel_id": channel.id,
                "message_id": message.message_id,
                "posted_at": message.posted_at.isoformat()
                if message.posted_at
                else None,
                "views": message.views,
                "forwards": message.forwards,
                "is_origin": source.is_origin,
                "similarity": serializers._num(source.similarity),
                "text": message.normalized_text
                if channel.redistribute_content
                else None,
            }
        )

    titles = await _channel_titles(
        session, {news.origin_channel_id} if news.origin_channel_id else set()
    )
    return {
        "news": serializers.serialize_news(
            news, titles.get(news.origin_channel_id)
        ),
        "sources": sources,
    }


@router.get("/signals")
async def list_signals(
    confidence_min: int = Query(0, ge=0, le=100),
    direction: str | None = None,
    asset: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    statement = (
        select(SignalRow).order_by(SignalRow.created_at.desc()).limit(limit)
    )
    if confidence_min:
        statement = statement.where(SignalRow.confidence >= confidence_min)
    if direction:
        statement = statement.where(SignalRow.direction == direction.upper())
    if asset:
        statement = statement.where(SignalRow.asset == asset.upper())
    if status:
        statement = statement.where(SignalRow.status == status)
    rows = (await session.scalars(statement)).all()
    return [serializers.serialize_signal(row) for row in rows]


@router.get("/signal/{signal_id}")
async def get_signal(
    signal_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    signal = await session.get(SignalRow, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="signal not found")
    news = await session.get(News, signal.news_id) if signal.news_id else None
    return {
        "signal": serializers.serialize_signal(signal),
        "news": serializers.serialize_news(news) if news else None,
    }


@router.post("/signal/{signal_id}/execute")
async def execute_signal(
    signal_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    signal = await session.get(SignalRow, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="signal not found")
    if settings.trading_mode == "paper":
        raise HTTPException(
            status_code=409, detail="paper mode: live execution is disabled"
        )
    raise HTTPException(status_code=501, detail="live execution not implemented")


@router.get("/portfolio")
async def get_portfolio(session: AsyncSession = Depends(get_session)) -> dict:
    equity = settings.paper_equity
    now = datetime.now(timezone.utc)
    open_trades = (
        await session.scalars(
            select(PaperTrade)
            .where(PaperTrade.closed_at.is_(None))
            .order_by(PaperTrade.opened_at.desc())
        )
    ).all()

    risk_rows = (
        await session.execute(
            select(SignalRow.risk_pct)
            .join(PaperTrade, PaperTrade.signal_id == SignalRow.id)
            .where(PaperTrade.closed_at.is_(None))
        )
    ).all()
    open_risk_amount = sum(float(row[0] or 0.0) for row in risk_rows) * equity

    async def realized(since: datetime | None) -> float:
        statement = select(func.coalesce(func.sum(PaperTrade.pnl), 0)).where(
            PaperTrade.closed_at.is_not(None)
        )
        if since is not None:
            statement = statement.where(PaperTrade.closed_at >= since)
        total = await session.scalar(statement)
        return float(total or 0.0)

    return {
        "mode": settings.trading_mode,
        "equity": equity,
        "open_risk_amount": open_risk_amount,
        "open_risk_pct": open_risk_amount / equity * 100.0 if equity else 0.0,
        "open_positions": [
            serializers.serialize_trade(trade, "paper") for trade in open_trades
        ],
        "realized_pnl_total": await realized(None),
        "realized_pnl_day": await realized(now - timedelta(days=1)),
        "realized_pnl_week": await realized(now - timedelta(days=7)),
    }


@router.get("/trades")
async def list_trades(
    mode: str | None = Query(None, pattern="^(paper|live)$"),
    status: str | None = Query(None, pattern="^(open|closed)$"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    results: list[dict] = []

    if mode in (None, "paper"):
        statement = select(PaperTrade).order_by(PaperTrade.opened_at.desc()).limit(limit)
        if status == "open":
            statement = statement.where(PaperTrade.closed_at.is_(None))
        elif status == "closed":
            statement = statement.where(PaperTrade.closed_at.is_not(None))
        for trade in (await session.scalars(statement)).all():
            results.append(serializers.serialize_trade(trade, "paper"))

    if mode in (None, "live"):
        statement = select(Trade).order_by(Trade.opened_at.desc()).limit(limit)
        if status == "open":
            statement = statement.where(Trade.closed_at.is_(None))
        elif status == "closed":
            statement = statement.where(Trade.closed_at.is_not(None))
        for trade in (await session.scalars(statement)).all():
            results.append(serializers.serialize_trade(trade, "live"))

    results.sort(key=lambda row: row["opened_at"] or "", reverse=True)
    return results[:limit]


@router.get("/channels")
async def list_channels(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    rows = (
        await session.scalars(
            select(Channel).order_by(Channel.credibility.desc()).limit(limit)
        )
    ).all()
    return [serializers.serialize_channel(row) for row in rows]


@router.get("/kill-switch")
async def get_kill_switch() -> dict:
    return {"kill_switch": settings.kill_switch or await runtime.get_kill_switch()}


@router.post("/kill-switch")
async def set_kill_switch(body: KillSwitchUpdate) -> dict:
    enabled = await runtime.set_kill_switch(body.enabled)
    return {"kill_switch": enabled}


async def _stream_loop(ws: WebSocket, stream: str, event_type: str) -> None:
    client = get_client()
    last_id = "$"
    try:
        while True:
            response = await client.xread({stream: last_id}, block=15000, count=20)
            if not response:
                await ws.send_json({"type": "ping"})
                continue
            for _name, entries in response:
                for entry_id, fields in entries:
                    last_id = entry_id
                    payload = json.loads(fields.get("payload", "{}"))
                    await ws.send_json({"type": event_type, "data": payload})
    except WebSocketDisconnect:
        return
    except Exception:
        return


@ws_router.websocket("/ws/news")
async def ws_news(ws: WebSocket, token: str = Query(default="")) -> None:
    if not verify_token(token):
        await ws.close(code=4401)
        return
    await ws.accept()
    await _stream_loop(ws, FAST_ALERTS_STREAM, "news")


@ws_router.websocket("/ws/signals")
async def ws_signals(ws: WebSocket, token: str = Query(default="")) -> None:
    if not verify_token(token):
        await ws.close(code=4401)
        return
    await ws.accept()
    await _stream_loop(ws, SIGNALS_STREAM, "signal")
