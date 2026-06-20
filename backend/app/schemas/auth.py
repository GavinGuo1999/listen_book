from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)


class UserLogin(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    id: UUID
    username: str
    display_name: str
    is_admin: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
