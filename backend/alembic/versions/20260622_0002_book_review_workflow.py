"""add book review workflow

Revision ID: 20260622_0002
Revises: 20260616_0001
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260622_0002"
down_revision: str | None = "20260616_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("books", sa.Column("uploader_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "books",
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default="approved",
        ),
    )
    op.add_column("books", sa.Column("review_note", sa.Text(), nullable=True))
    op.create_index(op.f("ix_books_uploader_id"), "books", ["uploader_id"], unique=False)
    op.create_index(op.f("ix_books_review_status"), "books", ["review_status"], unique=False)
    op.create_foreign_key(
        op.f("fk_books_uploader_id_users"),
        "books",
        "users",
        ["uploader_id"],
        ["id"],
    )
    op.alter_column("books", "review_status", server_default=None)


def downgrade() -> None:
    op.drop_constraint(op.f("fk_books_uploader_id_users"), "books", type_="foreignkey")
    op.drop_index(op.f("ix_books_review_status"), table_name="books")
    op.drop_index(op.f("ix_books_uploader_id"), table_name="books")
    op.drop_column("books", "review_note")
    op.drop_column("books", "review_status")
    op.drop_column("books", "uploader_id")
