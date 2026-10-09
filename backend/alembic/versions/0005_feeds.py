"""channel feed sources

Revision ID: 0005_feeds
Revises: 0004_notifications
Create Date: 2026-01-05 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "0005_feeds"
down_revision = "0004_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "channels",
        sa.Column(
            "kind", sa.Text(), nullable=False, server_default="telegram"
        ),
    )
    op.add_column("channels", sa.Column("feed_url", sa.Text()))
    op.add_column(
        "channels",
        sa.Column(
            "poll_interval_seconds",
            sa.Integer(),
            nullable=False,
            server_default="300",
        ),
    )
    op.add_column(
        "channels", sa.Column("last_polled_at", sa.DateTime(timezone=True))
    )
    op.create_index("ix_channels_kind", "channels", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_channels_kind", table_name="channels")
    op.drop_column("channels", "last_polled_at")
    op.drop_column("channels", "poll_interval_seconds")
    op.drop_column("channels", "feed_url")
    op.drop_column("channels", "kind")
