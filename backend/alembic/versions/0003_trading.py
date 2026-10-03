"""signals, orders, trades, candles, channel stats

Revision ID: 0003_trading
Revises: 0002_analysis
Create Date: 2026-01-03 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_trading"
down_revision = "0002_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signals",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("news_id", sa.BigInteger(), sa.ForeignKey("news.id")),
        sa.Column("asset", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("entry_low", sa.Numeric(), nullable=False),
        sa.Column("entry_high", sa.Numeric(), nullable=False),
        sa.Column("order_type", sa.Text(), nullable=False, server_default="limit"),
        sa.Column("stop_loss", sa.Numeric(), nullable=False),
        sa.Column("take_profits", postgresql.ARRAY(sa.Numeric()), nullable=False),
        sa.Column(
            "leverage_suggested", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("timeframe", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column(
            "market_risk_factor",
            sa.Numeric(4, 3),
            nullable=False,
            server_default="1.000",
        ),
        sa.Column("risk_pct", sa.Numeric(6, 4)),
        sa.Column("rationale", sa.Text()),
        sa.Column("risk_reward", sa.Numeric(6, 2)),
        sa.Column("status", sa.Text(), nullable=False, server_default="new"),
        sa.Column("prompt_version", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_signals_confidence", "signals", ["confidence", "created_at"])

    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("signal_id", sa.Text(), sa.ForeignKey("signals.id")),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("client_order_id", sa.Text(), nullable=False, unique=True),
        sa.Column("exchange_order_id", sa.Text()),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("order_type", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="entry"),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("price", sa.Numeric()),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("raw_response", postgresql.JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "trades",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("signal_id", sa.Text(), sa.ForeignKey("signals.id")),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("asset", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("entry_price", sa.Numeric(), nullable=False),
        sa.Column("exit_price", sa.Numeric()),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("pnl", sa.Numeric()),
        sa.Column("pnl_pct", sa.Numeric()),
        sa.Column("fees", sa.Numeric()),
        sa.Column("funding", sa.Numeric()),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("close_reason", sa.Text()),
    )

    op.create_table(
        "paper_trades",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("signal_id", sa.Text(), sa.ForeignKey("signals.id")),
        sa.Column("asset", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("entry_price", sa.Numeric(), nullable=False),
        sa.Column("exit_price", sa.Numeric()),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("pnl", sa.Numeric()),
        sa.Column("pnl_pct", sa.Numeric()),
        sa.Column("fees", sa.Numeric()),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("close_reason", sa.Text()),
    )

    op.create_table(
        "candles",
        sa.Column("symbol", sa.Text(), primary_key=True),
        sa.Column("timeframe", sa.Text(), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("open", sa.Numeric(), nullable=False),
        sa.Column("high", sa.Numeric(), nullable=False),
        sa.Column("low", sa.Numeric(), nullable=False),
        sa.Column("close", sa.Numeric(), nullable=False),
        sa.Column("volume", sa.Numeric(), nullable=False),
    )

    op.create_table(
        "channel_stats",
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey("channels.id"), primary_key=True
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("signals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_confidence", sa.Numeric(5, 2)),
        sa.Column("avg_pnl_pct", sa.Numeric(6, 3)),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("channel_stats")
    op.drop_table("candles")
    op.drop_table("paper_trades")
    op.drop_table("trades")
    op.drop_table("orders")
    op.drop_index("ix_signals_confidence", table_name="signals")
    op.drop_table("signals")
