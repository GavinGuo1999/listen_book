"""add book review audit events

Revision ID: 20260623_0003
Revises: 20260622_0002
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260623_0003"
down_revision: str | None = "20260622_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "book_review_events",
        sa.Column("book_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_review_status", sa.String(length=32), nullable=False),
        sa.Column("to_review_status", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_book_review_events_book_id"),
        "book_review_events",
        ["book_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_book_review_events_reviewer_id"),
        "book_review_events",
        ["reviewer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_book_review_events_to_review_status"),
        "book_review_events",
        ["to_review_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_book_review_events_to_review_status"),
        table_name="book_review_events",
    )
    op.drop_index(op.f("ix_book_review_events_reviewer_id"), table_name="book_review_events")
    op.drop_index(op.f("ix_book_review_events_book_id"), table_name="book_review_events")
    op.drop_table("book_review_events")
