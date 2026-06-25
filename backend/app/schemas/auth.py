from uuid import UUID

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str = ""
    password: str = ""


class UserLogin(BaseModel):
    username: str = ""
    password: str = ""


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
