from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SignalRow(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    news_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("news.id"))
    asset: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(Text)
    entry_low: Mapped[Decimal] = mapped_column(Numeric)
    entry_high: Mapped[Decimal] = mapped_column(Numeric)
    order_type: Mapped[str] = mapped_column(Text, default="limit")
    stop_loss: Mapped[Decimal] = mapped_column(Numeric)
    take_profits: Mapped[list[Decimal]] = mapped_column(ARRAY(Numeric))
    leverage_suggested: Mapped[int] = mapped_column(Integer, default=1)
    timeframe: Mapped[str] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer)
    market_risk_factor: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("1.000")
    )
    risk_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    rationale: Mapped[str | None] = mapped_column(Text)
    risk_reward: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    status: Mapped[str] = mapped_column(Text, default="new")
    prompt_version: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    signal_id: Mapped[str | None] = mapped_column(Text, ForeignKey("signals.id"))
    exchange: Mapped[str] = mapped_column(Text)
    symbol: Mapped[str] = mapped_column(Text)
    client_order_id: Mapped[str] = mapped_column(Text, unique=True)
    exchange_order_id: Mapped[str | None] = mapped_column(Text)
    side: Mapped[str] = mapped_column(Text)
    order_type: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, default="entry")
    quantity: Mapped[Decimal] = mapped_column(Numeric)
    price: Mapped[Decimal | None] = mapped_column(Numeric)
    status: Mapped[str] = mapped_column(Text, default="pending")
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    signal_id: Mapped[str | None] = mapped_column(Text, ForeignKey("signals.id"))
    mode: Mapped[str] = mapped_column(Text)
    asset: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(Text)
    entry_price: Mapped[Decimal] = mapped_column(Numeric)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric)
    quantity: Mapped[Decimal] = mapped_column(Numeric)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric)
    pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric)
    fees: Mapped[Decimal | None] = mapped_column(Numeric)
    funding: Mapped[Decimal | None] = mapped_column(Numeric)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(Text)


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    signal_id: Mapped[str | None] = mapped_column(Text, ForeignKey("signals.id"))
    asset: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(Text)
    entry_price: Mapped[Decimal] = mapped_column(Numeric)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric)
    quantity: Mapped[Decimal] = mapped_column(Numeric)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric)
    pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric)
    fees: Mapped[Decimal | None] = mapped_column(Numeric)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(Text)


class Candle(Base):
    __tablename__ = "candles"

    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    timeframe: Mapped[str] = mapped_column(Text, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric)
    high: Mapped[Decimal] = mapped_column(Numeric)
    low: Mapped[Decimal] = mapped_column(Numeric)
    close: Mapped[Decimal] = mapped_column(Numeric)
    volume: Mapped[Decimal] = mapped_column(Numeric)


class ChannelStat(Base):
    __tablename__ = "channel_stats"

    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channels.id"), primary_key=True
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    signals: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    avg_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    avg_pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
