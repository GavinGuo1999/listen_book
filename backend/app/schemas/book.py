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


class BookReviewUpdate(BaseModel):
    review_status: str = Field(pattern="^(approved|rejected|pending_review)$")
    review_note: str | None = None


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
