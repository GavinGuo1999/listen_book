from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminJobRead(BaseModel):
    id: UUID
    job_type: str
    status: str
    target_id: str | None
    attempts: int
    max_attempts: int
    error_message: str | None
    next_retry_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
