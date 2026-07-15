from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audio import AudioAsset, AudioStatus
from app.models.book import (
    Book,
    BookFile,
    BookReviewStatus,
    BookStatus,
    Chapter,
    Paragraph,
    Sentence,
)
from app.models.job import Job
from app.models.progress import ReadingProgress
from app.models.user import User
from app.services.auth import bootstrap_admin_user
from app.services.text_splitter import text_hash
from app.workers import jobs


def test_books_require_authentication(client: TestClient) -> None:
    client.cookies.clear()

    response = client.get("/api/books")

    assert response.status_code == 401


def test_upload_txt_parses_book_to_ready(client: TestClient, db_session: Session) -> None:
    headers = auth_headers(register_admin_user(client, db_session))
    response = client.post(
        "/api/books",
        headers=headers,
        files={"file": ("sample.txt", "第一句。第二句？".encode(), "text/plain")},
    )

    assert response.status_code == 201
    book_id = response.json()["id"]
    drain_jobs(db_session)

    books_response = client.get("/api/books", headers=headers)
    assert books_response.status_code == 200
    [book] = books_response.json()
    assert book["id"] == book_id
    assert book["status"] == BookStatus.READY.value
    assert book["review_status"] == BookReviewStatus.APPROVED.value

    chapters_response = client.get(f"/api/books/{book_id}/chapters", headers=headers)
    assert chapters_response.status_code == 200
    chapters = chapters_response.json()
    assert len(chapters) == 1
    sentences = chapters[0]["paragraphs"][0]["sentences"]
    assert [sentence["text"] for sentence in sentences] == ["第一句。", "第二句？"]


def test_upload_gb18030_txt_parses_book_to_ready(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = auth_headers(register_admin_user(client, db_session))
    response = client.post(
        "/api/books",
        headers=headers,
        files={"file": ("gb.txt", "增广贤文。".encode("gb18030"), "text/plain")},
    )

    assert response.status_code == 201
    book_id = response.json()["id"]
    drain_jobs(db_session)

    chapters_response = client.get(f"/api/books/{book_id}/chapters", headers=headers)
    assert chapters_response.status_code == 200
    sentences = chapters_response.json()[0]["paragraphs"][0]["sentences"]
    assert sentences[0]["text"] == "增广贤文。"


def test_upload_epub_parses_spine_chapters_to_ready(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    headers = auth_headers(register_admin_user(client, db_session))
    epub_path = tmp_path / "sample.epub"
    create_minimal_epub(epub_path)

    response = client.post(
        "/api/books",
        headers=headers,
        files={"file": ("sample.epub", epub_path.read_bytes(), "application/epub+zip")},
    )

    assert response.status_code == 201
    book_id = response.json()["id"]
    drain_jobs(db_session)

    books_response = client.get("/api/books", headers=headers)
    assert books_response.status_code == 200
    assert books_response.json()[0]["status"] == BookStatus.READY.value

    chapters_response = client.get(f"/api/books/{book_id}/chapters", headers=headers)
    assert chapters_response.status_code == 200
    chapters = chapters_response.json()
    assert [chapter["title"] for chapter in chapters] == ["第一章", "第二章"]

    first_chapter_sentences = [
        sentence["text"]
        for paragraph in chapters[0]["paragraphs"]
        for sentence in paragraph["sentences"]
    ]
    second_chapter_sentences = [
        sentence["text"]
        for paragraph in chapters[1]["paragraphs"]
        for sentence in paragraph["sentences"]
    ]
    assert first_chapter_sentences == ["第一句。", "第二句？"]
    assert second_chapter_sentences == ["第三句！"]


def test_upload_invalid_epub_marks_book_failed(client: TestClient, db_session: Session) -> None:
    headers = auth_headers(register_admin_user(client, db_session))
    response = client.post(
        "/api/books",
        headers=headers,
        files={"file": ("broken.epub", b"not a zip", "application/epub+zip")},
    )

    assert response.status_code == 201
    book_id = response.json()["id"]
    drain_jobs(db_session)

    books_response = client.get("/api/books", headers=headers)
    assert books_response.status_code == 200
    [book] = books_response.json()
    assert book["id"] == book_id
    assert book["status"] == BookStatus.FAILED.value


def test_user_upload_waits_for_admin_approval_before_public_visibility(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = register_admin_user(client, db_session)
    uploader_token = register_user(client, "uploader")
    other_token = register_user(client, "other-reader")

    upload_response = client.post(
        "/api/books",
        headers={"Authorization": f"Bearer {uploader_token}"},
        files={"file": ("pending.txt", "第一句。第二句。".encode(), "text/plain")},
    )

    assert upload_response.status_code == 201
    uploaded_book = upload_response.json()
    book_id = uploaded_book["id"]
    assert uploaded_book["status"] == BookStatus.UPLOADED.value
    assert uploaded_book["review_status"] == BookReviewStatus.PENDING.value
    drain_jobs(db_session)

    uploader_books_response = client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {uploader_token}"},
    )
    other_books_response = client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert uploader_books_response.status_code == 200
    assert [book["id"] for book in uploader_books_response.json()] == [book_id]
    assert uploader_books_response.json()[0]["status"] == BookStatus.READY.value
    assert other_books_response.status_code == 200
    assert book_id not in [book["id"] for book in other_books_response.json()]

    other_chapters_response = client.get(
        f"/api/books/{book_id}/chapters",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    uploader_chapters_response = client.get(
        f"/api/books/{book_id}/chapters",
        headers={"Authorization": f"Bearer {uploader_token}"},
    )
    assert other_chapters_response.status_code == 404
    assert uploader_chapters_response.status_code == 200

    legacy_admin_reviews_response = client.get(
        "/api/books/admin/reviews",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert legacy_admin_reviews_response.status_code == 200

    admin_reviews_response = client.get(
        "/api/admin/books/reviews",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_reviews_response.status_code == 200
    admin_review_book = next(
        book for book in admin_reviews_response.json() if book["id"] == book_id
    )
    assert admin_review_book["uploader_username"] == "uploader"
    assert admin_review_book["uploader_display_name"] == "uploader"
    assert admin_review_book["review_history"] == []

    forbidden_admin_reviews_response = client.get(
        "/api/admin/books/reviews",
        headers={"Authorization": f"Bearer {uploader_token}"},
    )
    assert forbidden_admin_reviews_response.status_code == 403

    forbidden_review_response = client.patch(
        f"/api/admin/books/{book_id}/review",
        headers={"Authorization": f"Bearer {uploader_token}"},
        json={"review_status": BookReviewStatus.APPROVED.value},
    )
    assert forbidden_review_response.status_code == 403

    approved_response = client.patch(
        f"/api/admin/books/{book_id}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "review_status": BookReviewStatus.APPROVED.value,
            "review_note": "内容完整，批准发布。",
        },
    )
    assert approved_response.status_code == 200
    assert approved_response.json()["review_status"] == BookReviewStatus.APPROVED.value
    assert approved_response.json()["review_note"] == "内容完整，批准发布。"

    approved_admin_reviews_response = client.get(
        "/api/admin/books/reviews",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    approved_admin_review_book = next(
        book for book in approved_admin_reviews_response.json() if book["id"] == book_id
    )
    review_event = approved_admin_review_book["review_history"][0]
    assert review_event["reviewer_username"] == "admin"
    assert review_event["reviewer_display_name"] == "admin"
    assert review_event["from_review_status"] == BookReviewStatus.PENDING.value
    assert review_event["to_review_status"] == BookReviewStatus.APPROVED.value
    assert review_event["note"] == "内容完整，批准发布。"
    assert review_event["created_at"]

    public_books_response = client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    public_chapters_response = client.get(
        f"/api/books/{book_id}/chapters",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert public_books_response.status_code == 200
    assert book_id in [book["id"] for book in public_books_response.json()]
    assert public_chapters_response.status_code == 200


def test_progress_api_saves_reads_and_validates_sentence(
    client: TestClient,
    db_session: Session,
) -> None:
    book, sentence = create_ready_book(db_session)
    headers = auth_headers(register_user(client, "reader"))

    empty_response = client.get(f"/api/books/{book.id}/progress", headers=headers)
    assert empty_response.status_code == 200
    assert empty_response.json() is None

    save_response = client.put(
        f"/api/books/{book.id}/progress",
        headers=headers,
        json={"sentence_id": str(sentence.id), "audio_position_ms": 8500},
    )
    assert save_response.status_code == 200
    payload = save_response.json()
    assert payload["book_id"] == str(book.id)
    assert payload["sentence_id"] == str(sentence.id)
    assert payload["audio_position_ms"] == 8500

    read_response = client.get(f"/api/books/{book.id}/progress", headers=headers)
    assert read_response.status_code == 200
    assert read_response.json()["audio_position_ms"] == 8500

    other_book, other_sentence = create_ready_book(db_session, title="Other")
    invalid_response = client.put(
        f"/api/books/{book.id}/progress",
        headers=headers,
        json={"sentence_id": str(other_sentence.id), "audio_position_ms": 1},
    )
    assert invalid_response.status_code == 400
    assert invalid_response.json()["detail"] == "Sentence does not belong to this book"

    missing_response = client.get(f"/api/books/{uuid4()}/progress", headers=headers)
    assert missing_response.status_code == 404

    assert other_book.id != book.id


def test_delete_book_cleans_database_rows_and_storage_files(
    client: TestClient,
    db_session: Session,
) -> None:
    book, sentence = create_ready_book(db_session, title="Delete Me")
    headers = auth_headers(register_admin_user(client, db_session))

    source_path = settings.uploads_dir / "delete-me.txt"
    source_path.write_text("正文。", encoding="utf-8")
    db_session.add(
        BookFile(
            book_id=book.id,
            original_filename="delete-me.txt",
            file_format="txt",
            storage_path=str(source_path),
            size_bytes=source_path.stat().st_size,
        )
    )

    audio_path = settings.audio_dir / "delete-me.mp3"
    audio_path.write_bytes(b"fake mp3")
    db_session.add(
        AudioAsset(
            sentence_id=sentence.id,
            model_name="edge-tts",
            model_version="test",
            voice="test-voice",
            speed=100,
            text_hash=sentence.text_hash,
            status=AudioStatus.READY.value,
            storage_path=str(audio_path),
            duration_ms=1000,
        )
    )

    user = db_session.query(User).filter(User.username == "admin").one()
    db_session.add(
        ReadingProgress(
            user_id=user.id,
            book_id=book.id,
            chapter_id=sentence.paragraph.chapter.id,
            paragraph_id=sentence.paragraph_id,
            sentence_id=sentence.id,
            audio_position_ms=1000,
        )
    )
    db_session.add(
        Job(
            job_type="parse_book",
            status="done",
            payload={"book_id": str(book.id), "storage_path": str(source_path), "format": "txt"},
        )
    )
    db_session.commit()

    response = client.delete(f"/api/books/{book.id}", headers=headers)
    assert response.status_code == 204

    assert db_session.get(Book, book.id) is None
    assert db_session.scalars(select(Chapter).where(Chapter.book_id == book.id)).all() == []
    assert db_session.scalars(select(Paragraph)).all() == []
    assert db_session.scalars(select(Sentence)).all() == []
    assert db_session.scalars(select(AudioAsset)).all() == []
    assert db_session.scalars(select(ReadingProgress)).all() == []
    assert db_session.scalars(select(Job)).all() == []
    assert not source_path.exists()
    assert not audio_path.exists()

    missing_response = client.delete(f"/api/books/{book.id}", headers=headers)
    assert missing_response.status_code == 404


def create_ready_book(db_session: Session, title: str = "Sample") -> tuple[Book, Sentence]:
    book = Book(title=title, status=BookStatus.READY.value)
    db_session.add(book)
    db_session.flush()

    chapter = Chapter(book_id=book.id, title="正文", chapter_index=0)
    db_session.add(chapter)
    db_session.flush()

    paragraph = Paragraph(chapter_id=chapter.id, paragraph_index=0, text="第一句。")
    db_session.add(paragraph)
    db_session.flush()

    sentence = Sentence(
        paragraph_id=paragraph.id,
        sentence_index=0,
        text="第一句。",
        text_hash=text_hash("第一句。"),
    )
    db_session.add(sentence)
    db_session.commit()
    db_session.refresh(book)
    db_session.refresh(sentence)
    return book, sentence


def register_user(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def register_admin_user(client: TestClient, db_session: Session, username: str = "admin") -> str:
    bootstrap_admin_user(db_session, username=username, password="secret123")
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def drain_jobs(db_session: Session, max_jobs: int = 20) -> None:
    for _ in range(max_jobs):
        if jobs.run_once(retry_base_seconds=0) == 0:
            break
    else:
        raise AssertionError("Job queue did not become idle")
    db_session.expire_all()


def create_minimal_epub(path) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as epub:
        epub.writestr("mimetype", "application/epub+zip", compress_type=0)
        epub.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
        epub.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf">
  <manifest>
    <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
    <itemref idref="chap2"/>
  </spine>
</package>
""",
        )
        epub.writestr(
            "OEBPS/chapter1.xhtml",
            """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>第一章</title><style>p { color: red; }</style></head>
  <body><h1>第一章</h1><p>第一句。第二句？</p></body>
</html>
""",
        )
        epub.writestr(
            "OEBPS/chapter2.xhtml",
            """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>第二章</title></head>
  <body><h1>第二章</h1><p>第三句！</p></body>
</html>
""",
        )
