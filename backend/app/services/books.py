import logging
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.audio import AudioAsset
from app.models.book import (
    Book,
    BookFile,
    BookReviewEvent,
    BookReviewStatus,
    Chapter,
    Paragraph,
    Sentence,
)
from app.models.job import Job, JobType
from app.models.progress import ReadingProgress
from app.models.user import User
from app.services.jobs import enqueue_job

SUPPORTED_FORMATS = {"txt", "epub"}
logger = logging.getLogger(__name__)


def list_visible_books(db: Session, user: User) -> list[Book]:
    stmt = select(Book).order_by(Book.created_at.desc())
    if not user.is_admin:
        stmt = stmt.where(
            or_(
                Book.review_status == BookReviewStatus.APPROVED.value,
                Book.uploader_id == user.id,
            )
        )
    return list(db.scalars(stmt).all())


def list_admin_review_books(db: Session) -> list[Book]:
    stmt = (
        select(Book)
        .options(
            selectinload(Book.uploader),
            selectinload(Book.review_events).selectinload(BookReviewEvent.reviewer),
        )
        .order_by(Book.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def create_uploaded_book(db: Session, file: UploadFile, uploader: User) -> Book:
    original_name = file.filename or "untitled"
    extension = Path(original_name).suffix.lower().lstrip(".")
    if extension not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported book format: {extension or 'unknown'}",
        )

    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid4()}.{extension}"
    storage_path = settings.uploads_dir / storage_name

    with storage_path.open("wb") as target:
        shutil.copyfileobj(file.file, target)

    size_bytes = storage_path.stat().st_size
    title = Path(original_name).stem

    book = Book(
        title=title,
        uploader_id=uploader.id,
        review_status=(
            BookReviewStatus.APPROVED.value
            if uploader.is_admin
            else BookReviewStatus.PENDING.value
        ),
    )
    db.add(book)
    db.flush()

    db.add(
        BookFile(
            book_id=book.id,
            original_filename=original_name,
            file_format=extension,
            storage_path=str(storage_path),
            size_bytes=size_bytes,
        )
    )
    enqueue_job(
        db,
        job_type=JobType.PARSE_BOOK.value,
        payload={
            "book_id": str(book.id),
            "storage_path": str(storage_path),
            "format": extension,
        },
        dedupe_key=f"parse:{book.id}",
        priority=10,
    )
    db.commit()
    db.refresh(book)
    return book


def review_book(
    db: Session,
    book_id: UUID,
    *,
    reviewer: User,
    review_status: str,
    review_note: str | None = None,
) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    previous_review_status = book.review_status
    cleaned_note = review_note.strip() if review_note and review_note.strip() else None
    book.review_status = review_status
    book.review_note = cleaned_note
    db.add(
        BookReviewEvent(
            book_id=book.id,
            reviewer_id=reviewer.id,
            from_review_status=previous_review_status,
            to_review_status=review_status,
            note=cleaned_note,
        )
    )
    db.commit()
    db.refresh(book)
    return book


def ensure_book_accessible(db: Session, book_id: UUID, user: User) -> Book:
    book = db.get(Book, book_id)
    if book is None or not can_access_book(book, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


def can_access_book(book: Book, user: User) -> bool:
    return (
        book.review_status == BookReviewStatus.APPROVED.value
        or user.is_admin
        or book.uploader_id == user.id
    )


def ensure_sentence_accessible(db: Session, sentence_id: UUID, user: User) -> Sentence:
    row = db.execute(
        select(Sentence, Book)
        .join(Paragraph, Sentence.paragraph_id == Paragraph.id)
        .join(Chapter, Paragraph.chapter_id == Chapter.id)
        .join(Book, Chapter.book_id == Book.id)
        .where(Sentence.id == sentence_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sentence not found: {sentence_id}",
        )

    sentence, book = row
    if not can_access_book(book, user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sentence not found: {sentence_id}",
        )
    return sentence


def ensure_chapter_accessible(db: Session, chapter_id: UUID, user: User) -> Chapter:
    row = db.execute(
        select(Chapter, Book)
        .join(Book, Chapter.book_id == Book.id)
        .where(Chapter.id == chapter_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
    chapter, book = row
    if not can_access_book(book, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
    return chapter


def delete_book(db: Session, book_id: UUID, user: User) -> None:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if not can_delete_book(book, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required",
        )

    file_paths = _collect_book_storage_paths(db, book)

    sentence_ids = list(
        db.scalars(
            select(Sentence.id)
            .join(Paragraph, Sentence.paragraph_id == Paragraph.id)
            .join(Chapter, Paragraph.chapter_id == Chapter.id)
            .where(Chapter.book_id == book_id)
        ).all()
    )

    if sentence_ids:
        for audio_asset in db.scalars(
            select(AudioAsset).where(AudioAsset.sentence_id.in_(sentence_ids))
        ).all():
            db.delete(audio_asset)

    for progress in db.scalars(
        select(ReadingProgress).where(ReadingProgress.book_id == book_id)
    ).all():
        db.delete(progress)

    for job in db.scalars(select(Job)).all():
        if job.payload.get("book_id") == str(book_id):
            db.delete(job)

    db.delete(book)
    db.commit()

    for file_path in file_paths:
        _delete_storage_file(file_path)


def can_delete_book(book: Book, user: User) -> bool:
    if user.is_admin:
        return True
    return book.uploader_id == user.id and book.review_status != BookReviewStatus.APPROVED.value


def _collect_book_storage_paths(db: Session, book: Book) -> list[Path]:
    paths: list[Path] = []

    if book.cover_path:
        paths.append(Path(book.cover_path))

    paths.extend(Path(book_file.storage_path) for book_file in book.files)

    audio_paths = db.scalars(
        select(AudioAsset.storage_path)
        .join(Sentence, AudioAsset.sentence_id == Sentence.id)
        .join(Paragraph, Sentence.paragraph_id == Paragraph.id)
        .join(Chapter, Paragraph.chapter_id == Chapter.id)
        .where(Chapter.book_id == book.id)
        .where(AudioAsset.storage_path.is_not(None))
    ).all()
    paths.extend(Path(path) for path in audio_paths if path)

    return paths


def _delete_storage_file(path: Path) -> None:
    try:
        resolved_path = path.resolve()
        storage_root = settings.storage_root.resolve()
        if not resolved_path.is_relative_to(storage_root):
            logger.warning("Skip deleting file outside storage root: %s", resolved_path)
            return
        if resolved_path.is_file():
            resolved_path.unlink()
    except OSError:
        logger.exception("Failed to delete storage file: %s", path)
