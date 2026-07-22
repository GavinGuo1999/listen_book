from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AdminUserRead(BaseModel):
    id: UUID
    username: str
    display_name: str
    is_admin: bool
    is_active: bool
    uploaded_book_count: int = 0
    created_at: datetime
    updated_at: datetime


class AdminUserList(BaseModel):
    items: list[AdminUserRead]
    total: int
    page: int
    page_size: int


class AdminUserUpdate(BaseModel):
    is_admin: bool | None = None
    is_active: bool | None = None


class AdminAuditEventRead(BaseModel):
    id: UUID
    actor_id: UUID
    actor_username: str | None = None
    target_user_id: UUID | None
    target_username: str | None = None
    action: str
    details: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class SystemCheckRead(BaseModel):
    key: str
    label: str
    status: Literal["ok", "warning", "error"]
    message: str


class WorkerStatusRead(BaseModel):
    worker_id: str
    hostname: str
    process_id: int
    started_at: datetime
    last_seen_at: datetime
    is_online: bool


class SystemStatusRead(BaseModel):
    status: Literal["ok", "warning", "error"]
    version: str
    checked_at: datetime
    checks: list[SystemCheckRead]
    workers: list[WorkerStatusRead]
