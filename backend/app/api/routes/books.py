import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.book import Book, Chapter, Paragraph
from app.models.user import User
from app.schemas.book import (
    BookSummary,
    ChapterRead,
    ReadingProgressRead,
    ReadingProgressUpdate,
)
from app.services.books import create_uploaded_book, delete_book
from app.services.progress import get_book_progress, save_book_progress
from app.workers.parse_books import run_once

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
BookUpload = Annotated[UploadFile, File(...)]
logger = logging.getLogger(__name__)


def run_pending_parse_job() -> None:
    try:
        run_once()
    except Exception:
        # The worker records job/book failure details before re-raising.
        logger.exception("Background book parsing failed")


@router.get("", response_model=list[BookSummary])
def list_books(db: DbSession) -> list[Book]:
    return list(db.scalars(select(Book).order_by(Book.created_at.desc())).all())


@router.post("", response_model=BookSummary, status_code=status.HTTP_201_CREATED)
def upload_book(file: BookUpload, db: DbSession, background_tasks: BackgroundTasks) -> Book:
    book = create_uploaded_book(db, file)
    background_tasks.add_task(run_pending_parse_job)
    return book


@router.get("/{book_id}/chapters", response_model=list[ChapterRead])
def list_chapters(book_id: UUID, db: DbSession) -> list[Chapter]:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    stmt = (
        select(Chapter)
        .where(Chapter.book_id == book_id)
        .options(selectinload(Chapter.paragraphs).selectinload(Paragraph.sentences))
        .order_by(Chapter.chapter_index)
    )
    return list(db.scalars(stmt).all())


@router.get("/{book_id}/progress", response_model=ReadingProgressRead | None)
def read_book_progress(
    book_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ReadingProgressRead | None:
    return get_book_progress(db, book_id, current_user)


@router.put("/{book_id}/progress", response_model=ReadingProgressRead)
def update_book_progress(
    book_id: UUID,
    payload: ReadingProgressUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ReadingProgressRead:
    return save_book_progress(
        db,
        book_id,
        sentence_id=payload.sentence_id,
        audio_position_ms=payload.audio_position_ms,
        user=current_user,
    )


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_book(book_id: UUID, db: DbSession) -> None:
    delete_book(db, book_id)
