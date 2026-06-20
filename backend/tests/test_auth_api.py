from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.book import Book, BookStatus, Chapter, Paragraph, Sentence
from app.models.user import User
from app.services.progress import get_or_create_default_user
from app.services.text_splitter import text_hash


def test_register_login_and_me(client: TestClient) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={"username": "Alice", "password": "secret123", "display_name": "Alice Reader"},
    )

    assert register_response.status_code == 201
    register_payload = register_response.json()
    assert register_payload["token_type"] == "bearer"
    assert register_payload["access_token"]
    assert register_payload["user"]["username"] == "alice"
    assert register_payload["user"]["display_name"] == "Alice Reader"

    duplicate_response = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "secret123"},
    )
    assert duplicate_response.status_code == 409

    failed_login_response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    )
    assert failed_login_response.status_code == 401

    login_response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "alice"

    invalid_me_response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
    assert invalid_me_response.status_code == 401


def test_missing_auth_uses_default_local_user(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["username"] == "local"
    assert db_session.query(User).filter(User.username == "local").one()


def test_progress_is_isolated_by_authenticated_user(
    client: TestClient,
    db_session: Session,
) -> None:
    book, first_sentence, second_sentence = create_ready_book_with_two_sentences(db_session)
    alice_token = register_user(client, "alice")
    bob_token = register_user(client, "bob")

    alice_save_response = client.put(
        f"/api/books/{book.id}/progress",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"sentence_id": str(first_sentence.id), "audio_position_ms": 1000},
    )
    bob_save_response = client.put(
        f"/api/books/{book.id}/progress",
        headers={"Authorization": f"Bearer {bob_token}"},
        json={"sentence_id": str(second_sentence.id), "audio_position_ms": 2000},
    )

    assert alice_save_response.status_code == 200
    assert bob_save_response.status_code == 200

    alice_read_response = client.get(
        f"/api/books/{book.id}/progress",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    bob_read_response = client.get(
        f"/api/books/{book.id}/progress",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    local_read_response = client.get(f"/api/books/{book.id}/progress")

    assert alice_read_response.status_code == 200
    assert alice_read_response.json()["sentence_id"] == str(first_sentence.id)
    assert alice_read_response.json()["audio_position_ms"] == 1000
    assert bob_read_response.status_code == 200
    assert bob_read_response.json()["sentence_id"] == str(second_sentence.id)
    assert bob_read_response.json()["audio_position_ms"] == 2000
    assert local_read_response.status_code == 200
    assert local_read_response.json() is None

    assert get_or_create_default_user(db_session).username == "local"


def register_user(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def create_ready_book_with_two_sentences(
    db_session: Session,
) -> tuple[Book, Sentence, Sentence]:
    book = Book(title="Shared Book", status=BookStatus.READY.value)
    db_session.add(book)
    db_session.flush()

    chapter = Chapter(book_id=book.id, title="正文", chapter_index=0)
    db_session.add(chapter)
    db_session.flush()

    paragraph = Paragraph(chapter_id=chapter.id, paragraph_index=0, text="第一句。第二句。")
    db_session.add(paragraph)
    db_session.flush()

    first_sentence = Sentence(
        paragraph_id=paragraph.id,
        sentence_index=0,
        text="第一句。",
        text_hash=text_hash("第一句。"),
    )
    second_sentence = Sentence(
        paragraph_id=paragraph.id,
        sentence_index=1,
        text="第二句。",
        text_hash=text_hash("第二句。"),
    )
    db_session.add_all([first_sentence, second_sentence])
    db_session.commit()
    db_session.refresh(book)
    db_session.refresh(first_sentence)
    db_session.refresh(second_sentence)
    return book, first_sentence, second_sentence
