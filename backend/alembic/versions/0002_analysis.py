"""analysis status and evaluation tables

Revision ID: 0002_analysis
Revises: 0001_initial
Create Date: 2026-01-02 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_analysis"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "news",
        sa.Column(
            "analysis_status",
            sa.Text(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("news", sa.Column("discarded_reason", sa.Text()))
    op.create_index("ix_news_analysis_status", "news", ["analysis_status"])

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "eval_labels",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "raw_message_id", sa.BigInteger(), sa.ForeignKey("raw_messages.id")
        ),
        sa.Column("label_coins", postgresql.ARRAY(sa.Text())),
        sa.Column("label_event_type", sa.Text()),
        sa.Column("label_sentiment", sa.Text()),
        sa.Column("label_tradable", sa.Boolean()),
        sa.Column(
            "is_adversarial", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "labeled_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "prompt_version", sa.Text(), sa.ForeignKey("prompt_versions.id")
        ),
        sa.Column("coin_f1", sa.Numeric(5, 4)),
        sa.Column("event_accuracy", sa.Numeric(5, 4)),
        sa.Column("tradable_f1", sa.Numeric(5, 4)),
        sa.Column("injection_pass", sa.Boolean()),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("eval_runs")
    op.drop_table("eval_labels")
    op.drop_table("prompt_versions")
    op.drop_index("ix_news_analysis_status", table_name="news")
    op.drop_column("news", "discarded_reason")
    op.drop_column("news", "analysis_status")
