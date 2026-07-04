from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.book import Book
from app.models.user import User
from app.schemas.book import AdminBookReviewSummary, BookReviewUpdate, BookSummary
from app.services.books import list_admin_review_books, review_book

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
