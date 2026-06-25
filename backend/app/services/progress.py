from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.book import Chapter, Paragraph, Sentence
from app.models.progress import ReadingProgress
from app.models.user import User
from app.services.books import ensure_book_accessible


def get_book_progress(
    db: Session,
    book_id: UUID,
    user: User,
) -> ReadingProgress | None:
    ensure_book_accessible(db, book_id, user)
    return db.scalar(
        select(ReadingProgress).where(
            ReadingProgress.user_id == user.id,
            ReadingProgress.book_id == book_id,
        )
    )


def save_book_progress(
    db: Session,
    book_id: UUID,
    sentence_id: UUID | None,
    user: User,
    audio_position_ms: int = 0,
) -> ReadingProgress:
    ensure_book_accessible(db, book_id, user)

    chapter_id: UUID | None = None
    paragraph_id: UUID | None = None
    if sentence_id is not None:
        chapter_id, paragraph_id = _resolve_sentence_location(db, book_id, sentence_id)

    progress = db.scalar(
        select(ReadingProgress).where(
            ReadingProgress.user_id == user.id,
            ReadingProgress.book_id == book_id,
        )
    )
    if progress is None:
        progress = ReadingProgress(
            user_id=user.id,
            book_id=book_id,
            audio_position_ms=0,
        )
        db.add(progress)

    progress.chapter_id = chapter_id
    progress.paragraph_id = paragraph_id
    progress.sentence_id = sentence_id
    progress.audio_position_ms = max(0, audio_position_ms)
    db.commit()
    db.refresh(progress)
    return progress


def _resolve_sentence_location(db: Session, book_id: UUID, sentence_id: UUID) -> tuple[UUID, UUID]:
    row = db.execute(
        select(Chapter.id, Paragraph.id)
        .join(Paragraph, Paragraph.chapter_id == Chapter.id)
        .join(Sentence, Sentence.paragraph_id == Paragraph.id)
        .where(Chapter.book_id == book_id)
        .where(Sentence.id == sentence_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sentence does not belong to this book",
        )
    return row[0], row[1]
