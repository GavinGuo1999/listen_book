"""initial schema

Revision ID: 20260616_0001
Revises:
Create Date: 2026-06-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260616_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_path", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_books_status"), "books", ["status"], unique=False)
    op.create_index(op.f("ix_books_title"), "books", ["title"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_job_type"), "jobs", ["job_type"], unique=False)
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)

    op.create_table(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "book_files",
        sa.Column("book_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_format", sa.String(length=16), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "chapters",
        sa.Column("book_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id", "chapter_index"),
    )
    op.create_index(op.f("ix_chapters_book_id"), "chapters", ["book_id"], unique=False)

    op.create_table(
        "paragraphs",
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paragraph_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chapter_id", "paragraph_index"),
    )
    op.create_index(op.f("ix_paragraphs_chapter_id"), "paragraphs", ["chapter_id"], unique=False)

    op.create_table(
        "sentences",
        sa.Column("paragraph_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sentence_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paragraph_id"], ["paragraphs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("paragraph_id", "sentence_index"),
    )
    op.create_index(op.f("ix_sentences_paragraph_id"), "sentences", ["paragraph_id"], unique=False)
    op.create_index(op.f("ix_sentences_text_hash"), "sentences", ["text_hash"], unique=False)

    op.create_table(
        "audio_assets",
        sa.Column("sentence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.Column("voice", sa.String(length=120), nullable=False),
        sa.Column("speed", sa.Integer(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sentence_id"], ["sentences.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sentence_id",
            "model_name",
            "model_version",
            "voice",
            "speed",
            "text_hash",
        ),
    )
    op.create_index(
        op.f("ix_audio_assets_sentence_id"),
        "audio_assets",
        ["sentence_id"],
        unique=False,
    )
    op.create_index(op.f("ix_audio_assets_status"), "audio_assets", ["status"], unique=False)
    op.create_index(op.f("ix_audio_assets_text_hash"), "audio_assets", ["text_hash"], unique=False)

    op.create_table(
        "reading_progress",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("book_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("paragraph_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sentence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("audio_position_ms", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"]),
        sa.ForeignKeyConstraint(["paragraph_id"], ["paragraphs.id"]),
        sa.ForeignKeyConstraint(["sentence_id"], ["sentences.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "book_id"),
    )
    op.create_index(
        op.f("ix_reading_progress_book_id"),
        "reading_progress",
        ["book_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reading_progress_user_id"),
        "reading_progress",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reading_progress_user_id"), table_name="reading_progress")
    op.drop_index(op.f("ix_reading_progress_book_id"), table_name="reading_progress")
    op.drop_table("reading_progress")
    op.drop_index(op.f("ix_audio_assets_text_hash"), table_name="audio_assets")
    op.drop_index(op.f("ix_audio_assets_status"), table_name="audio_assets")
    op.drop_index(op.f("ix_audio_assets_sentence_id"), table_name="audio_assets")
    op.drop_table("audio_assets")
    op.drop_index(op.f("ix_sentences_text_hash"), table_name="sentences")
    op.drop_index(op.f("ix_sentences_paragraph_id"), table_name="sentences")
    op.drop_table("sentences")
    op.drop_index(op.f("ix_paragraphs_chapter_id"), table_name="paragraphs")
    op.drop_table("paragraphs")
    op.drop_index(op.f("ix_chapters_book_id"), table_name="chapters")
    op.drop_table("chapters")
    op.drop_table("book_files")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_job_type"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_index(op.f("ix_books_title"), table_name="books")
    op.drop_index(op.f("ix_books_status"), table_name="books")
    op.drop_table("books")
