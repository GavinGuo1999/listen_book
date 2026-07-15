from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audio import AudioAsset, AudioStatus
from app.models.book import Book, BookStatus, Chapter, Paragraph, Sentence
from app.models.job import Job, JobStatus, JobType
from app.services.text_splitter import text_hash
from app.services.tts import TTSRequest, TTSResult
from app.workers import jobs


class FakeTTSProvider:
    model_name = "fake-tts"
    model_version = "1"

    def __init__(self, *, should_fail: bool = False) -> None:
        self.calls = 0
        self.should_fail = should_fail

    def generate(self, request: TTSRequest) -> TTSResult:
        self.calls += 1
        if self.should_fail:
            raise RuntimeError("fake provider failure")

        settings.audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = settings.audio_dir / f"fake-{self.calls}.mp3"
        audio_path.write_bytes(b"fake mp3 bytes")
        return TTSResult(audio_path=str(audio_path), duration_ms=1234)


@pytest.fixture
def fake_tts(monkeypatch: pytest.MonkeyPatch) -> FakeTTSProvider:
    provider = FakeTTSProvider()
    monkeypatch.setattr("app.services.audio.default_tts_provider", provider)
    return provider


def test_generate_sentence_audio_creates_ready_asset_and_serves_file(
    client: TestClient,
    db_session: Session,
    fake_tts: FakeTTSProvider,
) -> None:
    _book, sentence = create_ready_book(db_session)
    headers = auth_headers(register_user(client))

    response = client.post(f"/api/audio/sentences/{sentence.id}", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["sentence_id"] == str(sentence.id)
    assert payload["status"] == AudioStatus.PENDING.value
    assert payload["audio_url"] is None
    assert fake_tts.calls == 0

    drain_jobs(db_session)
    status_response = client.post(
        "/api/audio/sentences/status",
        headers=headers,
        json={"sentence_ids": [str(sentence.id)]},
    )
    payload = status_response.json()[0]
    assert payload["status"] == AudioStatus.READY.value
    assert payload["audio_url"].startswith("/api/audio/assets/")
    assert payload["duration_ms"] == 1234
    assert fake_tts.calls == 1

    file_response = client.get(payload["audio_url"], headers=headers)
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "audio/mpeg"
    assert file_response.content == b"fake mp3 bytes"

    cached_response = client.post(f"/api/audio/sentences/{sentence.id}", headers=headers)
    assert cached_response.status_code == 200
    assert cached_response.json()["id"] == payload["id"]
    assert fake_tts.calls == 1


def test_generate_sentence_audio_validates_missing_sentence(
    client: TestClient,
    fake_tts: FakeTTSProvider,
) -> None:
    missing_sentence_id = uuid4()
    headers = auth_headers(register_user(client))
    response = client.post(f"/api/audio/sentences/{missing_sentence_id}", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == f"Sentence not found: {missing_sentence_id}"
    assert fake_tts.calls == 0


def test_generate_sentence_audio_marks_asset_failed_when_provider_fails(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _book, sentence = create_ready_book(db_session)
    headers = auth_headers(register_user(client))
    failing_provider = FakeTTSProvider(should_fail=True)
    monkeypatch.setattr("app.services.audio.default_tts_provider", failing_provider)

    response = client.post(f"/api/audio/sentences/{sentence.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == AudioStatus.PENDING.value
    [job] = db_session.query(Job).all()
    job.max_attempts = 1
    db_session.commit()
    drain_jobs(db_session)
    assert failing_provider.calls == 1

    [asset] = db_session.query(AudioAsset).all()
    assert asset.status == AudioStatus.FAILED.value
    assert asset.error_message == "fake provider failure"
    failed_job = db_session.get(Job, job.id)
    assert failed_job is not None
    assert failed_job.status == JobStatus.FAILED.value

    working_provider = FakeTTSProvider()
    monkeypatch.setattr("app.services.audio.default_tts_provider", working_provider)
    retry_response = client.post(f"/api/audio/sentences/{sentence.id}", headers=headers)

    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == AudioStatus.PENDING.value
    assert retry_response.json()["id"] == str(asset.id)
    drain_jobs(db_session)
    ready_response = client.post(
        "/api/audio/sentences/status",
        headers=headers,
        json={"sentence_ids": [str(sentence.id)]},
    )
    assert ready_response.json()[0]["status"] == AudioStatus.READY.value
    assert working_provider.calls == 1


def test_prefetch_queues_pending_audio_and_status_reports_it(
    client: TestClient,
    db_session: Session,
    fake_tts: FakeTTSProvider,
) -> None:
    _book, sentence = create_ready_book(db_session)
    headers = auth_headers(register_user(client))
    response = client.post(
        "/api/audio/sentences/prefetch",
        headers=headers,
        json={"sentence_ids": [str(sentence.id)]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["queued_sentence_ids"] == [str(sentence.id)]
    assert payload["assets"][0]["sentence_id"] == str(sentence.id)
    assert payload["assets"][0]["status"] == AudioStatus.PENDING.value
    assert payload["assets"][0]["audio_url"] is None
    assert fake_tts.calls == 0
    [job] = db_session.query(Job).all()
    assert job.job_type == JobType.GENERATE_AUDIO.value
    assert job.status == JobStatus.PENDING.value

    status_response = client.post(
        "/api/audio/sentences/status",
        headers=headers,
        json={"sentence_ids": [str(sentence.id)]},
    )

    assert status_response.status_code == 200
    assert status_response.json()[0]["status"] == AudioStatus.PENDING.value


def test_prefetch_and_status_validate_missing_sentence(
    client: TestClient,
    fake_tts: FakeTTSProvider,
) -> None:
    missing_sentence_id = uuid4()
    headers = auth_headers(register_user(client))

    prefetch_response = client.post(
        "/api/audio/sentences/prefetch",
        headers=headers,
        json={"sentence_ids": [str(missing_sentence_id)]},
    )
    status_response = client.post(
        "/api/audio/sentences/status",
        headers=headers,
        json={"sentence_ids": [str(missing_sentence_id)]},
    )

    assert prefetch_response.status_code == 404
    assert prefetch_response.json()["detail"] == f"Sentence not found: {missing_sentence_id}"
    assert status_response.status_code == 404
    assert status_response.json()["detail"] == f"Sentence not found: {missing_sentence_id}"
    assert fake_tts.calls == 0


def test_chapter_prefetch_queues_chapter_and_sentence_audio_jobs(
    client: TestClient,
    db_session: Session,
    fake_tts: FakeTTSProvider,
) -> None:
    _book, sentence = create_ready_book(db_session, title="Chapter Prefetch")
    chapter_id = db_session.get(Paragraph, sentence.paragraph_id).chapter_id
    headers = auth_headers(register_user(client, username="chapter-prefetch-reader"))

    response = client.post(f"/api/audio/chapters/{chapter_id}/prefetch", headers=headers)

    assert response.status_code == 200
    assert response.json()["queued_sentence_ids"] == [str(sentence.id)]
    [chapter_job] = db_session.query(Job).all()
    assert chapter_job.job_type == JobType.PREFETCH_CHAPTER_AUDIO.value
    assert chapter_job.status == JobStatus.PENDING.value

    assert jobs.run_once(retry_base_seconds=0) == 1
    db_session.expire_all()
    audio_job = db_session.query(Job).filter(Job.job_type == JobType.GENERATE_AUDIO.value).one()
    assert audio_job.status == JobStatus.PENDING.value

    assert jobs.run_once(retry_base_seconds=0) == 1
    db_session.expire_all()
    asset = db_session.query(AudioAsset).one()
    assert asset.status == AudioStatus.READY.value
    assert fake_tts.calls == 1


def test_audio_file_endpoint_rejects_unready_missing_and_outside_storage_assets(
    client: TestClient,
    db_session: Session,
    fake_tts: FakeTTSProvider,
    tmp_path: Path,
) -> None:
    headers = auth_headers(register_user(client))
    _book, pending_sentence = create_ready_book(db_session, title="Pending Audio")
    pending_asset = AudioAsset(
        sentence_id=pending_sentence.id,
        model_name=fake_tts.model_name,
        model_version=fake_tts.model_version,
        voice="zh-CN-XiaoxiaoNeural",
        speed=100,
        text_hash=pending_sentence.text_hash,
        status=AudioStatus.PENDING.value,
    )
    db_session.add(pending_asset)
    db_session.commit()

    pending_response = client.get(f"/api/audio/assets/{pending_asset.id}/file", headers=headers)
    assert pending_response.status_code == 409

    _book, missing_sentence = create_ready_book(db_session, title="Missing Audio File")
    missing_path_asset = make_audio_asset(
        db_session,
        missing_sentence,
        fake_tts,
        storage_path=str(settings.audio_dir / "missing.mp3"),
    )
    missing_response = client.get(
        f"/api/audio/assets/{missing_path_asset.id}/file",
        headers=headers,
    )
    assert missing_response.status_code == 404

    _book, outside_sentence = create_ready_book(db_session, title="Outside Audio File")
    outside_path = tmp_path / "outside.mp3"
    outside_path.write_bytes(b"outside")
    outside_asset = make_audio_asset(
        db_session,
        outside_sentence,
        fake_tts,
        storage_path=str(outside_path),
    )
    outside_response = client.get(f"/api/audio/assets/{outside_asset.id}/file", headers=headers)
    assert outside_response.status_code == 404

    not_found_response = client.get(f"/api/audio/assets/{uuid4()}/file", headers=headers)
    assert not_found_response.status_code == 404


def create_ready_book(db_session: Session, title: str = "Audio Sample") -> tuple[Book, Sentence]:
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


def make_audio_asset(
    db_session: Session,
    sentence: Sentence,
    provider: FakeTTSProvider,
    *,
    storage_path: str,
) -> AudioAsset:
    asset = AudioAsset(
        sentence_id=sentence.id,
        model_name=provider.model_name,
        model_version=provider.model_version,
        voice="zh-CN-XiaoxiaoNeural",
        speed=100,
        text_hash=sentence.text_hash,
        status=AudioStatus.READY.value,
        storage_path=storage_path,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


def register_user(client: TestClient, username: str = "audio-reader") -> str:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 201
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
