"""Metrics collection backed by shared state (Postgres + Redis).

Workers run in separate processes, so per-process counters would not
aggregate. Instead we derive metrics on demand from the shared datastore:
row counts/status breakdowns from Postgres and stream depth/consumer lag
from Redis. The result can be rendered as Prometheus text or JSON.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import time

from sqlalchemy import func, select

from app.models.ingestion import Channel
from app.models.news import News
from app.models.trading import Order, PaperTrade, SignalRow, Trade
from app.services.ingestion import health, queue

STREAMS: dict[str, str] = {
    "raw_news": queue.RAW_STREAM,
    "clustered_news": queue.CLUSTERED_STREAM,
    "analyzed_news": queue.ANALYZED_STREAM,
    "signals": queue.SIGNALS_STREAM,
    "fast_alerts": queue.FAST_ALERTS_STREAM,
    "dlq": queue.DLQ_STREAM,
}


@dataclass(frozen=True)
class Sample:
    name: str
    value: float
    type: str = "gauge"
    help: str = ""
    labels: tuple[tuple[str, str], ...] = field(default_factory=tuple)


async def _group_counts(session, column) -> dict[str, int]:
    rows = await session.execute(
        select(column, func.count()).group_by(column)
    )
    return {str(key): int(count) for key, count in rows.all()}


async def _news_counts(session) -> dict[str, int]:
    return await _group_counts(session, News.analysis_status)


async def _signal_counts(session) -> dict[str, int]:
    return await _group_counts(session, SignalRow.status)


async def _order_counts(session) -> dict[str, int]:
    return await _group_counts(session, Order.status)


async def _count(session, stmt) -> int:
    return int(await session.scalar(stmt) or 0)


async def _sum(session, stmt) -> float:
    return float(await session.scalar(stmt) or 0.0)


async def _open_risk_pct(session) -> float:
    risk_sum = await _sum(
        session,
        select(func.coalesce(func.sum(SignalRow.risk_pct), 0))
        .select_from(SignalRow)
        .join(PaperTrade, PaperTrade.signal_id == SignalRow.id)
        .where(PaperTrade.closed_at.is_(None)),
    )
    return risk_sum * 100.0


async def _paper_stats(session) -> dict[str, float]:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    return {
        "open": await _count(
            session,
            select(func.count())
            .select_from(PaperTrade)
            .where(PaperTrade.closed_at.is_(None)),
        ),
        "closed": await _count(
            session,
            select(func.count())
            .select_from(PaperTrade)
            .where(PaperTrade.closed_at.is_not(None)),
        ),
        "realized_pnl": await _sum(
            session,
            select(func.coalesce(func.sum(PaperTrade.pnl), 0)).where(
                PaperTrade.closed_at.is_not(None)
            ),
        ),
        "realized_pnl_day": await _sum(
            session,
            select(func.coalesce(func.sum(PaperTrade.pnl), 0)).where(
                PaperTrade.closed_at.is_not(None),
                PaperTrade.closed_at >= day_ago,
            ),
        ),
        "realized_pnl_week": await _sum(
            session,
            select(func.coalesce(func.sum(PaperTrade.pnl), 0)).where(
                PaperTrade.closed_at.is_not(None),
                PaperTrade.closed_at >= week_ago,
            ),
        ),
        "open_risk_pct": await _open_risk_pct(session),
        "wins": await _count(
            session,
            select(func.count())
            .select_from(PaperTrade)
            .where(
                PaperTrade.closed_at.is_not(None), PaperTrade.pnl > 0
            ),
        ),
        "losses": await _count(
            session,
            select(func.count())
            .select_from(PaperTrade)
            .where(
                PaperTrade.closed_at.is_not(None), PaperTrade.pnl < 0
            ),
        ),
    }


async def _trade_stats(session) -> dict[str, float]:
    return {
        "open": await _count(
            session,
            select(func.count())
            .select_from(Trade)
            .where(Trade.closed_at.is_(None)),
        ),
        "closed": await _count(
            session,
            select(func.count())
            .select_from(Trade)
            .where(Trade.closed_at.is_not(None)),
        ),
        "realized_pnl": await _sum(
            session,
            select(func.coalesce(func.sum(Trade.pnl), 0)).where(
                Trade.closed_at.is_not(None)
            ),
        ),
    }


async def _channel_stats(session) -> dict[str, int]:
    return {
        "total": await _count(
            session, select(func.count()).select_from(Channel)
        ),
        "feed_active": await _count(
            session,
            select(func.count())
            .select_from(Channel)
            .where(Channel.kind == "feed", Channel.is_active.is_(True)),
        ),
        "telegram_active": await _count(
            session,
            select(func.count())
            .select_from(Channel)
            .where(Channel.kind == "telegram", Channel.is_active.is_(True)),
        ),
    }


async def _redis_samples(client) -> list[Sample]:
    samples: list[Sample] = []
    for label, stream in STREAMS.items():
        try:
            length = int(await client.xlen(stream))
        except Exception:
            length = 0
        samples.append(
            Sample(
                "newstrade_stream_length",
                length,
                help="Entries in the Redis stream",
                labels=(("stream", label),),
            )
        )
        try:
            groups = await client.xinfo_groups(stream)
        except Exception:
            groups = []
        for group in groups or []:
            name = str(group.get("name", ""))
            pending = int(group.get("pending") or 0)
            samples.append(
                Sample(
                    "newstrade_stream_pending",
                    pending,
                    help="Pending entries in the consumer group",
                    labels=(("stream", label), ("group", name)),
                )
            )
            lag = group.get("lag")
            if lag is not None:
                samples.append(
                    Sample(
                        "newstrade_stream_lag",
                        int(lag),
                        help="Undelivered entries in the stream",
                        labels=(("stream", label), ("group", name)),
                    )
                )
    return samples


async def _ingestor_samples(client) -> list[Sample]:
    state = await health.read_state(client)
    if not state:
        return []
    now = time.time()
    samples: list[Sample] = [
        Sample(
            "newstrade_ingestor_connected",
            1 if state.get("connected") == "1" else 0,
            help="Telegram ingestor connection state (1=connected)",
        ),
        Sample(
            "newstrade_ingestor_reconnects_total",
            int(state.get("reconnects") or 0),
            type="counter",
            help="Telegram ingestor reconnects since start",
        ),
    ]
    heartbeat = state.get("heartbeat")
    if heartbeat is not None:
        samples.append(
            Sample(
                "newstrade_ingestor_seconds_since_heartbeat",
                max(0.0, now - float(heartbeat)),
                help="Seconds since the ingestor last reported in",
            )
        )
    last_event = state.get("last_event")
    if last_event is not None:
        samples.append(
            Sample(
                "newstrade_ingestor_seconds_since_event",
                max(0.0, now - float(last_event)),
                help="Seconds since the ingestor last ingested a message",
            )
        )
    return samples


async def collect(session, client) -> list[Sample]:
    samples: list[Sample] = [
        Sample("newstrade_build_info", 1, help="Always 1; build marker")
    ]
    for status, count in (await _news_counts(session)).items():
        samples.append(
            Sample(
                "newstrade_news_total",
                count,
                type="counter",
                help="News items by analysis status",
                labels=(("status", status),),
            )
        )
    for status, count in (await _signal_counts(session)).items():
        samples.append(
            Sample(
                "newstrade_signals_total",
                count,
                type="counter",
                help="Signals by status",
                labels=(("status", status),),
            )
        )
    for status, count in (await _order_counts(session)).items():
        samples.append(
            Sample(
                "newstrade_orders_total",
                count,
                type="counter",
                help="Orders by status",
                labels=(("status", status),),
            )
        )

    paper = await _paper_stats(session)
    samples.extend(
        [
            Sample(
                "newstrade_paper_trades_open",
                paper["open"],
                help="Open paper trades",
            ),
            Sample(
                "newstrade_paper_trades_closed_total",
                paper["closed"],
                type="counter",
                help="Closed paper trades",
            ),
            Sample(
                "newstrade_paper_trades_wins_total",
                paper["wins"],
                type="counter",
                help="Winning closed paper trades",
            ),
            Sample(
                "newstrade_paper_trades_losses_total",
                paper["losses"],
                type="counter",
                help="Losing closed paper trades",
            ),
            Sample(
                "newstrade_paper_realized_pnl",
                paper["realized_pnl"],
                help="Realized paper PnL (quote currency)",
            ),
            Sample(
                "newstrade_paper_realized_pnl_day",
                paper["realized_pnl_day"],
                help="Realized paper PnL over the last 24h",
            ),
            Sample(
                "newstrade_paper_realized_pnl_week",
                paper["realized_pnl_week"],
                help="Realized paper PnL over the last 7 days",
            ),
            Sample(
                "newstrade_paper_open_risk_pct",
                paper["open_risk_pct"],
                help="Open paper risk as percent of equity",
            ),
        ]
    )

    trades = await _trade_stats(session)
    samples.extend(
        [
            Sample(
                "newstrade_trades_open", trades["open"], help="Open live trades"
            ),
            Sample(
                "newstrade_trades_closed_total",
                trades["closed"],
                type="counter",
                help="Closed live trades",
            ),
            Sample(
                "newstrade_trades_realized_pnl",
                trades["realized_pnl"],
                help="Realized live PnL (quote currency)",
            ),
        ]
    )

    channels = await _channel_stats(session)
    samples.extend(
        [
            Sample(
                "newstrade_channels_total",
                channels["total"],
                help="Registered channels (all kinds)",
            ),
            Sample(
                "newstrade_channels_active",
                channels["feed_active"],
                help="Active feed channels",
                labels=(("kind", "feed"),),
            ),
            Sample(
                "newstrade_channels_active",
                channels["telegram_active"],
                help="Active feed channels",
                labels=(("kind", "telegram"),),
            ),
        ]
    )

    samples.extend(await _redis_samples(client))
    samples.extend(await _ingestor_samples(client))
    return samples


def _fmt(value: float) -> str:
    if float(value) == int(value):
        return str(int(value))
    return repr(float(value))


def _label_str(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{key}="{value}"' for key, value in labels)
    return "{" + inner + "}"


def render(samples: list[Sample]) -> str:
    lines: list[str] = []
    announced: set[str] = set()
    for sample in samples:
        if sample.name not in announced:
            announced.add(sample.name)
            if sample.help:
                lines.append(f"# HELP {sample.name} {sample.help}")
            lines.append(f"# TYPE {sample.name} {sample.type}")
    for sample in samples:
        lines.append(
            f"{sample.name}{_label_str(sample.labels)} {_fmt(sample.value)}"
        )
    return "\n".join(lines) + "\n"


def to_dict(samples: list[Sample]) -> dict[str, float]:
    result: dict[str, float] = {}
    for sample in samples:
        result[sample.name + _label_str(sample.labels)] = sample.value
    return result
