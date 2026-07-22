from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.book import Book, BookReviewEvent, BookReviewStatus
from app.models.user import User
from app.services.auth import bootstrap_admin_user
from app.services.operations import record_worker_heartbeat


def test_admin_user_management_filters_updates_and_audits(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = create_admin(client, db_session, "operations-admin")
    regular_token = register(client, "managed-reader")
    reader = db_session.scalar(select(User).where(User.username == "managed-reader"))
    assert reader is not None
    db_session.add(
        Book(
            title="Managed upload",
            uploader_id=reader.id,
            review_status=BookReviewStatus.PENDING.value,
        )
    )
    db_session.commit()

    forbidden = client.get("/api/admin/users", headers=auth_headers(regular_token))
    response = client.get(
        "/api/admin/users?q=managed&status=active&role=user&page=1&page_size=10",
        headers=auth_headers(admin_token),
    )

    assert forbidden.status_code == 403
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    [user_payload] = payload["items"]
    assert user_payload["username"] == "managed-reader"
    assert user_payload["uploaded_book_count"] == 1
    assert user_payload["is_active"] is True

    grant_response = client.patch(
        f"/api/admin/users/{reader.id}",
        headers=auth_headers(admin_token),
        json={"is_admin": True},
    )
    disable_response = client.patch(
        f"/api/admin/users/{reader.id}",
        headers=auth_headers(admin_token),
        json={"is_active": False},
    )

    assert grant_response.status_code == 200
    assert grant_response.json()["is_admin"] is True
    assert disable_response.status_code == 200
    assert disable_response.json()["is_active"] is False
    assert client.get("/api/auth/me", headers=auth_headers(regular_token)).status_code == 401

    uploads_response = client.get(
        f"/api/admin/users/{reader.id}/books",
        headers=auth_headers(admin_token),
    )
    assert uploads_response.status_code == 200
    assert [book["title"] for book in uploads_response.json()] == ["Managed upload"]

    audit_response = client.get(
        "/api/admin/audit-events",
        headers=auth_headers(admin_token),
    )
    assert audit_response.status_code == 200
    actions = [event["action"] for event in audit_response.json()]
    assert actions[:2] == ["user_disabled", "admin_granted"]
    assert all(event["actor_username"] == "operations-admin" for event in audit_response.json())
    assert all(event["target_username"] == "managed-reader" for event in audit_response.json())


def test_admin_user_management_protects_current_and_bootstrap_admin(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    current_token = create_admin(client, db_session, "current-admin")
    current_admin = db_session.scalar(select(User).where(User.username == "current-admin"))
    assert current_admin is not None

    self_response = client.patch(
        f"/api/admin/users/{current_admin.id}",
        headers=auth_headers(current_token),
        json={"is_active": False},
    )
    assert self_response.status_code == 409
    assert "当前登录账号" in self_response.json()["detail"]

    bootstrap_admin_user(db_session, username="protected-admin", password="secret123")
    protected = db_session.scalar(select(User).where(User.username == "protected-admin"))
    assert protected is not None
    monkeypatch.setattr(settings, "bootstrap_admin_username", "protected-admin")

    protected_response = client.patch(
        f"/api/admin/users/{protected.id}",
        headers=auth_headers(current_token),
        json={"is_admin": False},
    )
    assert protected_response.status_code == 409
    assert "Bootstrap" in protected_response.json()["detail"]


def test_admin_batch_review_is_atomic_and_writes_each_book_event(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = create_admin(client, db_session, "batch-admin")
    uploader_token = register(client, "batch-uploader")
    uploader = db_session.scalar(select(User).where(User.username == "batch-uploader"))
    assert uploader is not None
    books = [
        Book(
            title=f"Batch {index}",
            uploader_id=uploader.id,
            review_status=BookReviewStatus.PENDING.value,
        )
        for index in range(2)
    ]
    db_session.add_all(books)
    db_session.commit()

    missing_response = client.post(
        "/api/admin/books/reviews/batch",
        headers=auth_headers(admin_token),
        json={
            "book_ids": [str(books[0].id), str(uuid4())],
            "review_status": "approved",
        },
    )
    assert missing_response.status_code == 404
    assert all(book.review_status == BookReviewStatus.PENDING.value for book in books)
    assert list(db_session.scalars(select(BookReviewEvent)).all()) == []

    forbidden = client.post(
        "/api/admin/books/reviews/batch",
        headers=auth_headers(uploader_token),
        json={
            "book_ids": [str(book.id) for book in books],
            "review_status": "approved",
        },
    )
    response = client.post(
        "/api/admin/books/reviews/batch",
        headers=auth_headers(admin_token),
        json={
            "book_ids": [str(book.id) for book in books],
            "review_status": "rejected",
            "review_note": "批量检查不通过",
        },
    )

    assert forbidden.status_code == 403
    assert response.status_code == 200
    assert {book["review_status"] for book in response.json()} == {"rejected"}
    events = list(db_session.scalars(select(BookReviewEvent)).all())
    assert len(events) == 2
    assert {event.book_id for event in events} == {book.id for book in books}
    assert {event.note for event in events} == {"批量检查不通过"}


def test_admin_system_status_reports_checks_and_online_worker(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "secret_key",
        "secure-local-secret-key-with-more-than-32-characters",
    )
    monkeypatch.setattr(settings, "bootstrap_admin_username", "status-admin")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "non-default-admin-password")
    admin_token = create_admin(client, db_session, "status-admin")
    regular_token = register(client, "status-reader")
    now = datetime.now(UTC)
    record_worker_heartbeat(
        db_session,
        worker_id="test-worker",
        hostname="test-host",
        process_id=123,
        started_at=now,
        now=now,
    )
    forbidden = client.get("/api/admin/system/status", headers=auth_headers(regular_token))
    response = client.get("/api/admin/system/status", headers=auth_headers(admin_token))

    assert forbidden.status_code == 403
    assert response.status_code == 200
    payload = response.json()
    checks = {check["key"]: check for check in payload["checks"]}
    assert checks["database"]["status"] == "ok"
    assert checks["storage"]["status"] == "ok"
    assert checks["secret_key"]["status"] == "ok"
    assert checks["admin_password"]["status"] == "ok"
    assert checks["worker"]["status"] == "ok"
    assert payload["workers"][0]["worker_id"] == "test-worker"
    assert payload["workers"][0]["is_online"] is True


def create_admin(client: TestClient, db_session: Session, username: str) -> str:
    bootstrap_admin_user(db_session, username=username, password="secret123")
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def register(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
