"""device tokens and notifications

Revision ID: 0004_notifications
Revises: 0003_trading
Create Date: 2026-01-04 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_notifications"
down_revision = "0003_trading"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("token", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "platform", sa.Text(), nullable=False, server_default="android"
        ),
        sa.Column("label", sa.Text()),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_device_tokens_token", "device_tokens", ["token"], unique=True
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "channel", sa.Text(), nullable=False, server_default="inapp"
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("signal_id", sa.Text(), sa.ForeignKey("signals.id")),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_notifications_created_at", "notifications", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_device_tokens_token", table_name="device_tokens")
    op.drop_table("device_tokens")
