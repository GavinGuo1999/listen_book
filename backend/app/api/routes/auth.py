from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, get_current_user
from app.models.user import User
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserRead
from app.services.auth import authenticate_user, create_access_token, create_user

router = APIRouter()
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/register", response_model=TokenResponse, status_code=201)
def register_user(payload: UserCreate, db: DbSession) -> TokenResponse:
    user = create_user(
        db,
        username=payload.username,
        password=payload.password,
        display_name=payload.display_name,
    )
    return TokenResponse(access_token=create_access_token(user), user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin, db: DbSession) -> TokenResponse:
    user = authenticate_user(db, username=payload.username, password=payload.password)
    return TokenResponse(access_token=create_access_token(user), user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: CurrentUser) -> User:
    return current_user
