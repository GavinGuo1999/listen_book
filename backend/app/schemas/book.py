from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BookSummary(BaseModel):
    id: UUID
    title: str
    author: str | None
    status: str
    review_status: str
    review_note: str | None = None
    uploader_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BookReviewEventRead(BaseModel):
    id: UUID
    reviewer_id: UUID | None
    reviewer_username: str | None = None
    reviewer_display_name: str | None = None
    from_review_status: str
    to_review_status: str
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminBookReviewSummary(BookSummary):
    uploader_username: str | None = None
    uploader_display_name: str | None = None
    review_history: list[BookReviewEventRead] = Field(default_factory=list)


class BookReviewUpdate(BaseModel):
    review_status: str = Field(pattern="^(approved|rejected|pending_review)$")
    review_note: str | None = None


class BookBatchReviewRequest(BaseModel):
    book_ids: list[UUID] = Field(min_length=1, max_length=100)
    review_status: str = Field(pattern="^(approved|rejected)$")
    review_note: str | None = Field(default=None, max_length=1000)


class SentenceRead(BaseModel):
    id: UUID
    sentence_index: int
    text: str

    model_config = {"from_attributes": True}


class ParagraphRead(BaseModel):
    id: UUID
    paragraph_index: int
    text: str
    sentences: list[SentenceRead]

    model_config = {"from_attributes": True}


class ChapterRead(BaseModel):
    id: UUID
    title: str
    chapter_index: int
    paragraphs: list[ParagraphRead]

    model_config = {"from_attributes": True}


class ReadingProgressRead(BaseModel):
    book_id: UUID
    chapter_id: UUID | None
    paragraph_id: UUID | None
    sentence_id: UUID | None
    audio_position_ms: int

    model_config = {"from_attributes": True}


class ReadingProgressUpdate(BaseModel):
    sentence_id: UUID | None = None
    audio_position_ms: int = 0
