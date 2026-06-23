import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class BookStatus(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    READY = "ready"
    FAILED = "failed"


class BookReviewStatus(StrEnum):
    PENDING = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Book(IdMixin, TimestampMixin, Base):
    __tablename__ = "books"

    title: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    cover_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), default=BookStatus.UPLOADED.value, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    uploader_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
    )
    review_status: Mapped[str] = mapped_column(
        String(32),
        default=BookReviewStatus.APPROVED.value,
        index=True,
    )
    review_note: Mapped[str | None] = mapped_column(Text)

    uploader = relationship("User", back_populates="uploaded_books")
    files = relationship("BookFile", back_populates="book", cascade="all, delete-orphan")
    chapters = relationship("Chapter", back_populates="book", cascade="all, delete-orphan")
    review_events = relationship(
        "BookReviewEvent",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by=lambda: BookReviewEvent.created_at.desc(),
    )

    @property
    def uploader_username(self) -> str | None:
        return self.uploader.username if self.uploader else None

    @property
    def uploader_display_name(self) -> str | None:
        return self.uploader.display_name if self.uploader else None

    @property
    def review_history(self) -> list["BookReviewEvent"]:
        return list(self.review_events)


class BookFile(IdMixin, TimestampMixin, Base):
    __tablename__ = "book_files"

    book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("books.id"))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_format: Mapped[str] = mapped_column(String(16))
    storage_path: Mapped[str] = mapped_column(String(500))
    size_bytes: Mapped[int] = mapped_column(Integer)

    book = relationship("Book", back_populates="files")


class BookReviewEvent(IdMixin, TimestampMixin, Base):
    __tablename__ = "book_review_events"

    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id"),
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
    )
    from_review_status: Mapped[str] = mapped_column(String(32))
    to_review_status: Mapped[str] = mapped_column(String(32), index=True)
    note: Mapped[str | None] = mapped_column(Text)

    book = relationship("Book", back_populates="review_events")
    reviewer = relationship("User")

    @property
    def reviewer_username(self) -> str | None:
        return self.reviewer.username if self.reviewer else None

    @property
    def reviewer_display_name(self) -> str | None:
        return self.reviewer.display_name if self.reviewer else None


class Chapter(IdMixin, TimestampMixin, Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("book_id", "chapter_index"),)

    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    chapter_index: Mapped[int] = mapped_column(Integer)

    book = relationship("Book", back_populates="chapters")
    paragraphs = relationship(
        "Paragraph",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="Paragraph.paragraph_index",
    )


class Paragraph(IdMixin, TimestampMixin, Base):
    __tablename__ = "paragraphs"
    __table_args__ = (UniqueConstraint("chapter_id", "paragraph_index"),)

    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chapters.id"),
        index=True,
    )
    paragraph_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    chapter = relationship("Chapter", back_populates="paragraphs")
    sentences = relationship(
        "Sentence",
        back_populates="paragraph",
        cascade="all, delete-orphan",
        order_by="Sentence.sentence_index",
    )


class Sentence(IdMixin, TimestampMixin, Base):
    __tablename__ = "sentences"
    __table_args__ = (UniqueConstraint("paragraph_id", "sentence_index"),)

    paragraph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paragraphs.id"),
        index=True,
    )
    sentence_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    text_hash: Mapped[str] = mapped_column(String(64), index=True)

    paragraph = relationship("Paragraph", back_populates="sentences")
    audio_assets = relationship("AudioAsset", back_populates="sentence")
