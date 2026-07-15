from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.book import Book
from app.models.job import Job
from app.models.user import User
from app.schemas.book import AdminBookReviewSummary, BookReviewUpdate, BookSummary
from app.schemas.job import AdminJobRead
from app.services.books import list_admin_review_books, review_book
from app.services.jobs import job_target_id, list_jobs, retry_job

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]


@router.get("/books/reviews", response_model=list[AdminBookReviewSummary])
def list_admin_book_reviews(db: DbSession, admin_user: AdminUser) -> list[Book]:
    del admin_user
    return list_admin_review_books(db)


@router.patch("/books/{book_id}/review", response_model=BookSummary)
def update_admin_book_review(
    book_id: UUID,
    payload: BookReviewUpdate,
    db: DbSession,
    admin_user: AdminUser,
) -> Book:
    return review_book(
        db,
        book_id,
        reviewer=admin_user,
        review_status=payload.review_status,
        review_note=payload.review_note,
    )


def to_admin_job_read(job: Job) -> AdminJobRead:
    return AdminJobRead(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        target_id=job_target_id(job),
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        error_message=job.error_message,
        next_retry_at=job.next_retry_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )


@router.get("/jobs", response_model=list[AdminJobRead])
def list_admin_jobs(
    db: DbSession,
    admin_user: AdminUser,
    status_filter: Literal["pending", "running", "done", "failed"] | None = Query(
        default=None,
        alias="status",
    ),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AdminJobRead]:
    del admin_user
    return [
        to_admin_job_read(job)
        for job in list_jobs(db, job_status=status_filter, limit=limit)
    ]


@router.post("/jobs/{job_id}/retry", response_model=AdminJobRead)
def retry_admin_job(job_id: UUID, db: DbSession, admin_user: AdminUser) -> AdminJobRead:
    del admin_user
    return to_admin_job_read(retry_job(db, job_id))
