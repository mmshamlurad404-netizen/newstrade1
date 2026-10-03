"""initial phase 1 tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "ingestion_accounts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False, unique=True),
        sa.Column("session_ref", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_flood_wait_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "channels",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.Text()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "redistribute_content",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "credibility",
            sa.Numeric(4, 3),
            nullable=False,
            server_default="0.500",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "account_id", sa.BigInteger(), sa.ForeignKey("ingestion_accounts.id")
        ),
        sa.Column("last_message_id", sa.BigInteger()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_channels_telegram_id", "channels", ["telegram_id"], unique=True
    )

    op.create_table(
        "raw_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("channel_id", sa.BigInteger(), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("original_text", sa.Text()),
        sa.Column("normalized_text", sa.Text()),
        sa.Column("links", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("media_type", sa.Text()),
        sa.Column("media_path", sa.Text()),
        sa.Column("ocr_text", sa.Text()),
        sa.Column("views", sa.Integer()),
        sa.Column("forwards", sa.Integer()),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("channel_id", "message_id", name="uq_raw_channel_msg"),
    )
    op.create_index("ix_raw_messages_channel_id", "raw_messages", ["channel_id"])
    op.create_index("ix_raw_messages_posted_at", "raw_messages", ["posted_at"])
    op.create_index("ix_raw_messages_content_hash", "raw_messages", ["content_hash"])

    op.create_table(
        "news",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("canonical_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text()),
        sa.Column("coins", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("event_type", sa.Text()),
        sa.Column("sentiment", sa.Text()),
        sa.Column("sentiment_score", sa.Numeric(4, 3)),
        sa.Column("urgency", sa.Text()),
        sa.Column("certainty", sa.Numeric(4, 3)),
        sa.Column("impact_timeframe", sa.Text()),
        sa.Column("market_scope", sa.Text()),
        sa.Column("asset_resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("embedding", Vector(1536)),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("origin_channel_id", sa.BigInteger(), sa.ForeignKey("channels.id")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prompt_version", sa.Text()),
        sa.Column("model_name", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_news_first_seen", "news", ["first_seen_at"])
    op.create_index(
        "ix_news_coins", "news", ["coins"], postgresql_using="gin"
    )
    op.create_index(
        "ix_news_embedding",
        "news",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "news_sources",
        sa.Column("news_id", sa.BigInteger(), sa.ForeignKey("news.id"), primary_key=True),
        sa.Column(
            "raw_message_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_messages.id"),
            primary_key=True,
        ),
        sa.Column("channel_id", sa.BigInteger(), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("is_origin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("similarity", sa.Numeric(4, 3), nullable=False, server_default="1.000"),
    )


def downgrade() -> None:
    op.drop_table("news_sources")
    op.drop_index("ix_news_embedding", table_name="news")
    op.drop_index("ix_news_coins", table_name="news")
    op.drop_index("ix_news_first_seen", table_name="news")
    op.drop_table("news")
    op.drop_index("ix_raw_messages_content_hash", table_name="raw_messages")
    op.drop_index("ix_raw_messages_posted_at", table_name="raw_messages")
    op.drop_index("ix_raw_messages_channel_id", table_name="raw_messages")
    op.drop_table("raw_messages")
    op.drop_index("ix_channels_telegram_id", table_name="channels")
    op.drop_table("channels")
    op.drop_table("ingestion_accounts")
