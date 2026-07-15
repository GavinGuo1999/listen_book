from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.job import Job, JobStatus, JobType
from app.services.auth import bootstrap_admin_user
from app.services.jobs import cleanup_completed_jobs, enqueue_job
from app.workers import jobs


def test_enqueue_job_deduplicates_active_work(db_session: Session) -> None:
    first, first_created = enqueue_job(
        db_session,
        job_type=JobType.GENERATE_AUDIO.value,
        payload={"sentence_id": "same-target"},
        dedupe_key="audio:same-target",
    )
    second, second_created = enqueue_job(
        db_session,
        job_type=JobType.GENERATE_AUDIO.value,
        payload={"sentence_id": "same-target"},
        dedupe_key="audio:same-target",
    )
    db_session.commit()

    assert first_created is True
    assert second_created is False
    assert second.id == first.id
    assert db_session.query(Job).count() == 1


def test_claim_next_job_respects_priority(db_session: Session) -> None:
    low_priority = Job(
        job_type="unsupported-low",
        status=JobStatus.PENDING.value,
        payload={},
        priority=100,
    )
    high_priority = Job(
        job_type="unsupported-high",
        status=JobStatus.PENDING.value,
        payload={},
        priority=10,
    )
    db_session.add_all([low_priority, high_priority])
    db_session.commit()

    claimed = jobs.claim_next_job(db_session)

    assert claimed is not None
    assert claimed.id == high_priority.id
    assert claimed.status == JobStatus.RUNNING.value
    assert claimed.attempts == 1
    assert claimed.started_at is not None


def test_worker_retries_then_marks_job_failed(db_session: Session) -> None:
    job = Job(
        job_type="unsupported-test-job",
        status=JobStatus.PENDING.value,
        payload={},
        max_attempts=2,
    )
    db_session.add(job)
    db_session.commit()

    assert jobs.run_once(retry_base_seconds=0) == 1
    db_session.expire_all()
    first_attempt = db_session.get(Job, job.id)
    assert first_attempt is not None
    assert first_attempt.status == JobStatus.PENDING.value
    assert first_attempt.attempts == 1
    assert first_attempt.next_retry_at is not None

    assert jobs.run_once(retry_base_seconds=0) == 1
    db_session.expire_all()
    final_attempt = db_session.get(Job, job.id)
    assert final_attempt is not None
    assert final_attempt.status == JobStatus.FAILED.value
    assert final_attempt.attempts == 2
    assert final_attempt.finished_at is not None
    assert "Unsupported job type" in (final_attempt.error_message or "")


def test_recover_stale_job_returns_it_to_queue(db_session: Session) -> None:
    stale_job = Job(
        job_type=JobType.PARSE_BOOK.value,
        status=JobStatus.RUNNING.value,
        payload={"book_id": "missing"},
        attempts=1,
        max_attempts=3,
        started_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    db_session.add(stale_job)
    db_session.commit()

    recovered = jobs.recover_stale_jobs(db_session, stale_after_seconds=60)
    db_session.commit()

    assert recovered == 1
    assert stale_job.status == JobStatus.PENDING.value
    assert stale_job.started_at is None
    assert stale_job.next_retry_at is not None
    assert "lease expired" in (stale_job.error_message or "")


def test_cleanup_completed_jobs_only_removes_expired_done_jobs(db_session: Session) -> None:
    now = datetime.now(UTC)
    expired_done = Job(
        job_type=JobType.GENERATE_AUDIO.value,
        status=JobStatus.DONE.value,
        payload={},
        finished_at=now - timedelta(days=31),
    )
    legacy_expired_done = Job(
        job_type=JobType.PARSE_BOOK.value,
        status=JobStatus.DONE.value,
        payload={},
        finished_at=None,
        updated_at=now - timedelta(days=31),
    )
    recent_done = Job(
        job_type=JobType.GENERATE_AUDIO.value,
        status=JobStatus.DONE.value,
        payload={},
        finished_at=now - timedelta(days=2),
    )
    expired_failed = Job(
        job_type=JobType.PARSE_BOOK.value,
        status=JobStatus.FAILED.value,
        payload={},
        finished_at=now - timedelta(days=90),
    )
    db_session.add_all([expired_done, legacy_expired_done, recent_done, expired_failed])
    db_session.commit()
    preserved_ids = {recent_done.id, expired_failed.id}

    deleted_count = cleanup_completed_jobs(db_session, retention_days=30, now=now)

    assert deleted_count == 2
    assert {job.id for job in db_session.query(Job).all()} == preserved_ids


def test_admin_can_list_and_retry_failed_jobs(client: TestClient, db_session: Session) -> None:
    admin = bootstrap_admin_user(
        db_session,
        username="job-admin",
        password="secret123",
    )
    assert admin is not None
    admin_token = login(client, "job-admin")
    regular_token = register(client, "job-reader")
    failed_job = Job(
        job_type=JobType.PARSE_BOOK.value,
        status=JobStatus.FAILED.value,
        payload={"book_id": "book-target", "storage_path": "sensitive-local-path"},
        attempts=3,
        max_attempts=3,
        error_message="parse failed",
        finished_at=datetime.now(UTC),
    )
    db_session.add(failed_job)
    db_session.commit()

    forbidden = client.get("/api/admin/jobs", headers=auth_headers(regular_token))
    response = client.get(
        "/api/admin/jobs?status=failed",
        headers=auth_headers(admin_token),
    )

    assert forbidden.status_code == 403
    assert response.status_code == 200
    [payload] = response.json()
    assert payload["id"] == str(failed_job.id)
    assert payload["target_id"] == "book-target"
    assert "payload" not in payload
    assert "sensitive-local-path" not in response.text

    retry_response = client.post(
        f"/api/admin/jobs/{failed_job.id}/retry",
        headers=auth_headers(admin_token),
    )
    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == JobStatus.PENDING.value
    assert retry_response.json()["attempts"] == 0


def register(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
