from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.book import Book
from app.models.job import Job
from app.models.user import User
from app.schemas.admin import (
    AdminAuditEventRead,
    AdminUserList,
    AdminUserRead,
    AdminUserUpdate,
    SystemStatusRead,
)
from app.schemas.book import (
    AdminBookReviewSummary,
    BookBatchReviewRequest,
    BookReviewUpdate,
    BookSummary,
)
from app.schemas.job import AdminJobRead
from app.services.books import list_admin_review_books, review_book, review_books
from app.services.jobs import job_target_id, list_jobs, retry_job
from app.services.operations import (
    list_admin_audit_events,
    list_admin_users,
    update_admin_user,
)
from app.services.system import read_system_status

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]


@router.get("/books/reviews", response_model=list[AdminBookReviewSummary])
def list_admin_book_reviews(db: DbSession, admin_user: AdminUser) -> list[Book]:
    del admin_user
    return list_admin_review_books(db)


@router.post("/books/reviews/batch", response_model=list[BookSummary])
def batch_update_admin_book_reviews(
    payload: BookBatchReviewRequest,
    db: DbSession,
    admin_user: AdminUser,
) -> list[Book]:
    return review_books(
        db,
        payload.book_ids,
        reviewer=admin_user,
        review_status=payload.review_status,
        review_note=payload.review_note,
    )


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


@router.get("/system/status", response_model=SystemStatusRead)
def get_admin_system_status(db: DbSession, admin_user: AdminUser) -> SystemStatusRead:
    del admin_user
    return read_system_status(db)


@router.get("/users", response_model=AdminUserList)
def get_admin_users(
    db: DbSession,
    admin_user: AdminUser,
    q: str = Query(default="", max_length=120),
    status_filter: Literal["all", "active", "disabled"] = Query(
        default="all",
        alias="status",
    ),
    role_filter: Literal["all", "admin", "user"] = Query(default="all", alias="role"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AdminUserList:
    del admin_user
    rows, total = list_admin_users(
        db,
        query=q,
        status_filter=status_filter,
        role_filter=role_filter,
        page=page,
        page_size=page_size,
    )
    return AdminUserList(
        items=[
            AdminUserRead(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                is_admin=user.is_admin,
                is_active=user.is_active,
                uploaded_book_count=upload_count,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            for user, upload_count in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/users/{user_id}", response_model=AdminUserRead)
def patch_admin_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    db: DbSession,
    admin_user: AdminUser,
) -> AdminUserRead:
    user = update_admin_user(
        db,
        user_id,
        actor=admin_user,
        is_admin=payload.is_admin,
        is_active=payload.is_active,
    )
    upload_count = len(list_admin_review_books(db, uploader_id=user.id))
    return AdminUserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_admin=user.is_admin,
        is_active=user.is_active,
        uploaded_book_count=upload_count,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/users/{user_id}/books", response_model=list[AdminBookReviewSummary])
def get_admin_user_books(
    user_id: UUID,
    db: DbSession,
    admin_user: AdminUser,
) -> list[Book]:
    del admin_user
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return list_admin_review_books(db, uploader_id=user_id)


@router.get("/audit-events", response_model=list[AdminAuditEventRead])
def get_admin_audit_events(
    db: DbSession,
    admin_user: AdminUser,
    limit: int = Query(default=100, ge=1, le=500),
) -> list:
    del admin_user
    return list_admin_audit_events(db, limit=limit)


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
