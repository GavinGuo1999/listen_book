from __future__ import annotations

import logging
import os
import signal
import socket
import threading
from datetime import UTC, datetime, timedelta
from time import monotonic
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.book import Book, BookStatus, Chapter, Paragraph, Sentence
from app.models.job import Job, JobStatus, JobType
from app.services.audio import generate_sentence_audio_asset, queue_sentence_audio
from app.services.jobs import cleanup_completed_jobs
from app.services.operations import record_worker_heartbeat
from app.workers.parse_books import parse_epub_book, parse_txt_book

logger = logging.getLogger(__name__)
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_STALE_AFTER_SECONDS = 300
DEFAULT_RETRY_BASE_SECONDS = 5


def claim_next_job(
    db: Session,
    *,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> Job | None:
    now = datetime.now(UTC)
    recover_stale_jobs(db, now=now, stale_after_seconds=stale_after_seconds)

    stmt = (
        select(Job)
        .where(
            Job.status == JobStatus.PENDING.value,
            Job.attempts < Job.max_attempts,
            or_(Job.next_retry_at.is_(None), Job.next_retry_at <= now),
        )
        .order_by(Job.priority, Job.created_at)
        .limit(1)
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)

    job = db.scalar(stmt)
    if job is None:
        db.commit()
        return None

    job.status = JobStatus.RUNNING.value
    job.attempts += 1
    job.error_message = None
    job.next_retry_at = None
    job.started_at = now
    job.finished_at = None
    db.commit()
    db.refresh(job)
    return job


def recover_stale_jobs(
    db: Session,
    *,
    now: datetime | None = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> int:
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(seconds=stale_after_seconds)
    stmt = select(Job).where(
        Job.status == JobStatus.RUNNING.value,
        Job.started_at.is_not(None),
        Job.started_at < cutoff,
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    stale_jobs = list(db.scalars(stmt).all())
    for job in stale_jobs:
        job.error_message = "Worker lease expired; job returned to queue"
        job.started_at = None
        if job.attempts >= job.max_attempts:
            job.status = JobStatus.FAILED.value
            job.finished_at = now
        else:
            job.status = JobStatus.PENDING.value
            job.next_retry_at = now
    return len(stale_jobs)


def run_once(
    *,
    retry_base_seconds: int = DEFAULT_RETRY_BASE_SECONDS,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> int:
    with SessionLocal() as db:
        job = claim_next_job(db, stale_after_seconds=stale_after_seconds)
    if job is None:
        return 0

    try:
        process_job(job)
    except Exception as exc:
        logger.exception("Job failed", extra={"job_id": str(job.id), "job_type": job.job_type})
        mark_job_failed(job.id, exc, retry_base_seconds=retry_base_seconds)
    else:
        mark_job_done(job.id)
    return 1


def process_job(job: Job) -> None:
    match job.job_type:
        case JobType.PARSE_BOOK.value:
            _process_parse_book(job)
        case JobType.GENERATE_AUDIO.value:
            _process_generate_audio(job)
        case JobType.PREFETCH_CHAPTER_AUDIO.value:
            _process_prefetch_chapter_audio(job)
        case unsupported_type:
            raise RuntimeError(f"Unsupported job type: {unsupported_type}")


def _process_parse_book(job: Job) -> None:
    match job.payload.get("format"):
        case "txt":
            parse_txt_book(job)
        case "epub":
            parse_epub_book(job)
        case unsupported_format:
            raise RuntimeError(f"Unsupported parse format: {unsupported_format}")


def _process_generate_audio(job: Job) -> None:
    sentence_id = UUID(job.payload["sentence_id"])
    with SessionLocal() as db:
        generate_sentence_audio_asset(db, sentence_id)


def _process_prefetch_chapter_audio(job: Job) -> None:
    chapter_id = UUID(job.payload["chapter_id"])
    with SessionLocal() as db:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None:
            raise RuntimeError(f"Chapter not found: {chapter_id}")
        sentences = list(
            db.scalars(
                select(Sentence)
                .join(Paragraph, Sentence.paragraph_id == Paragraph.id)
                .where(Paragraph.chapter_id == chapter_id)
                .order_by(Paragraph.paragraph_index, Sentence.sentence_index)
            ).all()
        )
        for sentence in sentences:
            queue_sentence_audio(db, sentence)


def mark_job_done(job_id: UUID) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.DONE.value
        job.finished_at = datetime.now(UTC)
        job.next_retry_at = None
        db.commit()


def mark_job_failed(job_id: UUID, exc: Exception, *, retry_base_seconds: int) -> None:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.error_message = str(exc)
        job.started_at = None
        if job.attempts >= job.max_attempts:
            job.status = JobStatus.FAILED.value
            job.finished_at = now
            _mark_target_failed(db, job, str(exc))
        else:
            delay_seconds = min(300, retry_base_seconds * (2 ** max(0, job.attempts - 1)))
            job.status = JobStatus.PENDING.value
            job.next_retry_at = now + timedelta(seconds=delay_seconds)
        db.commit()


def _mark_target_failed(db: Session, job: Job, error_message: str) -> None:
    if job.job_type != JobType.PARSE_BOOK.value:
        return
    book_id = job.payload.get("book_id")
    if not book_id:
        return
    book = db.get(Book, UUID(book_id))
    if book is not None:
        book.status = BookStatus.FAILED.value
        book.error_message = error_message


def run_forever(
    stop_event: threading.Event | None = None,
    *,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    cleanup_interval_seconds: int | None = None,
    heartbeat_interval_seconds: int | None = None,
    worker_id: str | None = None,
) -> None:
    stop_event = stop_event or threading.Event()
    cleanup_interval_seconds = cleanup_interval_seconds or settings.job_cleanup_interval_seconds
    heartbeat_interval_seconds = (
        heartbeat_interval_seconds or settings.worker_heartbeat_interval_seconds
    )
    hostname = socket.gethostname()
    process_id = os.getpid()
    worker_id = worker_id or f"{hostname}:{process_id}:{uuid4().hex[:8]}"
    worker_started_at = datetime.now(UTC)
    next_cleanup_at = 0.0
    next_heartbeat_at = 0.0
    logger.info("Listen Book worker started")
    while not stop_event.is_set():
        started = monotonic()
        if started >= next_heartbeat_at:
            try:
                publish_worker_heartbeat(
                    worker_id=worker_id,
                    hostname=hostname,
                    process_id=process_id,
                    started_at=worker_started_at,
                )
            except Exception:
                logger.exception("Worker heartbeat update failed")
            next_heartbeat_at = started + heartbeat_interval_seconds
        if started >= next_cleanup_at:
            try:
                deleted_count = cleanup_expired_completed_jobs()
                if deleted_count:
                    logger.info("Removed %s expired completed jobs", deleted_count)
            except Exception:
                logger.exception("Completed job cleanup failed")
            next_cleanup_at = started + cleanup_interval_seconds
        try:
            processed = run_once()
        except Exception:
            logger.exception("Worker loop failed before a job could be processed")
            stop_event.wait(poll_interval_seconds)
            continue
        if processed == 0:
            stop_event.wait(poll_interval_seconds)
        elif monotonic() - started < 0.01:
            stop_event.wait(0.01)
    logger.info("Listen Book worker stopped")


def cleanup_expired_completed_jobs() -> int:
    with SessionLocal() as db:
        return cleanup_completed_jobs(db, retention_days=settings.job_retention_days)


def publish_worker_heartbeat(
    *,
    worker_id: str,
    hostname: str,
    process_id: int,
    started_at: datetime,
) -> None:
    with SessionLocal() as db:
        record_worker_heartbeat(
            db,
            worker_id=worker_id,
            hostname=hostname,
            process_id=process_id,
            started_at=started_at,
        )


def main() -> None:
    stop_event = threading.Event()

    def request_stop(_signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)
    logging.basicConfig(level=logging.INFO)
    run_forever(stop_event)


if __name__ == "__main__":
    main()
