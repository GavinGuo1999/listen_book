"""add durable job queue fields

Revision ID: 20260715_0004
Revises: 20260623_0003
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260715_0004"
down_revision: str | None = "20260623_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("dedupe_key", sa.String(length=255), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
    )
    op.add_column(
        "jobs",
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column("jobs", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_jobs_dedupe_key"), "jobs", ["dedupe_key"], unique=False)
    op.create_index(op.f("ix_jobs_priority"), "jobs", ["priority"], unique=False)
    op.create_index(op.f("ix_jobs_next_retry_at"), "jobs", ["next_retry_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_next_retry_at"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_priority"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_dedupe_key"), table_name="jobs")
    op.drop_column("jobs", "finished_at")
    op.drop_column("jobs", "started_at")
    op.drop_column("jobs", "next_retry_at")
    op.drop_column("jobs", "max_attempts")
    op.drop_column("jobs", "priority")
    op.drop_column("jobs", "dedupe_key")
