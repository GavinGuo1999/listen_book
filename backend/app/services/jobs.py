from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from app.models.job import Job, JobStatus

ACTIVE_JOB_STATUSES = (JobStatus.PENDING.value, JobStatus.RUNNING.value)


def enqueue_job(
    db: Session,
    *,
    job_type: str,
    payload: dict,
    dedupe_key: str,
    priority: int = 100,
    max_attempts: int = 3,
) -> tuple[Job, bool]:
    existing = db.scalar(
        select(Job).where(
            Job.job_type == job_type,
            Job.dedupe_key == dedupe_key,
            Job.status.in_(ACTIVE_JOB_STATUSES),
        )
    )
    if existing is not None:
        return existing, False

    job = Job(
        job_type=job_type,
        status=JobStatus.PENDING.value,
        payload=payload,
        dedupe_key=dedupe_key,
        priority=priority,
        max_attempts=max_attempts,
    )
    db.add(job)
    db.flush()
    return job, True


def list_jobs(db: Session, *, job_status: str | None = None, limit: int = 100) -> list[Job]:
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
    if job_status:
        stmt = stmt.where(Job.status == job_status)
    return list(db.scalars(stmt).all())


def retry_job(db: Session, job_id: UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != JobStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed jobs can be retried",
        )

    job.status = JobStatus.PENDING.value
    job.attempts = 0
    job.error_message = None
    job.next_retry_at = None
    job.started_at = None
    job.finished_at = None
    job.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job


def cleanup_completed_jobs(
    db: Session,
    *,
    retention_days: int,
    now: datetime | None = None,
) -> int:
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)
    result = db.execute(
        delete(Job).where(
            Job.status == JobStatus.DONE.value,
            or_(
                Job.finished_at < cutoff,
                and_(Job.finished_at.is_(None), Job.updated_at < cutoff),
            ),
        )
    )
    db.commit()
    return result.rowcount or 0


def job_target_id(job: Job) -> str | None:
    for key in ("book_id", "sentence_id", "chapter_id"):
        value = job.payload.get(key)
        if value:
            return str(value)
    return None
