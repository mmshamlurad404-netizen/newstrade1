from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestionAccount(Base):
    __tablename__ = "ingestion_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    label: Mapped[str] = mapped_column(Text, unique=True)
    session_ref: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_flood_wait_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text, default="telegram", index=True)
    feed_url: Mapped[str | None] = mapped_column(Text)
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    redistribute_content: Mapped[bool] = mapped_column(Boolean, default=False)
    credibility: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("0.500")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    account_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ingestion_accounts.id")
    )
    last_message_id: Mapped[int | None] = mapped_column(BigInteger)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
