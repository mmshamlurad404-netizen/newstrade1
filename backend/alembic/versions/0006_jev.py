"""jev assessment on news

Revision ID: 0006_jev
Revises: 0005_feeds
Create Date: 2026-01-06 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_jev"
down_revision = "0005_feeds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "news",
        sa.Column("jev_assessment", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("news", "jev_assessment")
