from datetime import datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawMessage(Base):
    __tablename__ = "raw_messages"
    __table_args__ = (
        UniqueConstraint("channel_id", "message_id", name="uq_raw_channel_msg"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channels.id"), index=True
    )
    message_id: Mapped[int] = mapped_column(BigInteger)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    original_text: Mapped[str | None] = mapped_column(Text)
    normalized_text: Mapped[str | None] = mapped_column(Text)
    links: Mapped[list] = mapped_column(JSONB, default=list)
    media_type: Mapped[str | None] = mapped_column(Text)
    media_path: Mapped[str | None] = mapped_column(Text)
    ocr_text: Mapped[str | None] = mapped_column(Text)
    views: Mapped[int | None] = mapped_column(Integer)
    forwards: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(Text, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    canonical_hash: Mapped[str] = mapped_column(Text, unique=True)
    headline: Mapped[str] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    coins: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    event_type: Mapped[str | None] = mapped_column(Text)
    sentiment: Mapped[str | None] = mapped_column(Text)
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    urgency: Mapped[str | None] = mapped_column(Text)
    certainty: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    impact_timeframe: Mapped[str | None] = mapped_column(Text)
    market_scope: Mapped[str | None] = mapped_column(Text)
    asset_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    source_count: Mapped[int] = mapped_column(Integer, default=1)
    origin_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("channels.id")
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    prompt_version: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NewsSource(Base):
    __tablename__ = "news_sources"

    news_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("news.id"), primary_key=True
    )
    raw_message_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("raw_messages.id"), primary_key=True
    )
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.id"))
    is_origin: Mapped[bool] = mapped_column(Boolean, default=False)
    similarity: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("1.000"))
