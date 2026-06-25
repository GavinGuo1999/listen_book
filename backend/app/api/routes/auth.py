from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import DbSession, get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserRead
from app.services.auth import authenticate_user, create_access_token, create_user

router = APIRouter()
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/register", response_model=TokenResponse, status_code=201)
def register_user(payload: UserCreate, db: DbSession, response: Response) -> TokenResponse:
    user = create_user(
        db,
        username=payload.username,
        password=payload.password,
    )
    token = create_access_token(user)
    set_session_cookie(response, token)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin, db: DbSession, response: Response) -> TokenResponse:
    user = authenticate_user(db, username=payload.username, password=payload.password)
    token = create_access_token(user)
    set_session_cookie(response, token)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/logout", status_code=204)
def logout_user(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        samesite="lax",
        secure=settings.session_cookie_secure,
        httponly=True,
    )


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: CurrentUser) -> User:
    return current_user


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
        max_age=30 * 24 * 60 * 60,
    )
