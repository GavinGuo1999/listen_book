from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audio import AudioAsset, AudioStatus
from app.models.book import Book, BookStatus, Chapter, Paragraph, Sentence
from app.services.text_splitter import text_hash
from app.services.tts import TTSRequest, TTSResult


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

    response = client.post(f"/api/audio/sentences/{sentence.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sentence_id"] == str(sentence.id)
    assert payload["status"] == AudioStatus.READY.value
    assert payload["audio_url"].startswith("/api/audio/assets/")
    assert payload["duration_ms"] == 1234
    assert fake_tts.calls == 1

    file_response = client.get(payload["audio_url"])
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "audio/mpeg"
    assert file_response.content == b"fake mp3 bytes"

    cached_response = client.post(f"/api/audio/sentences/{sentence.id}")
    assert cached_response.status_code == 200
    assert cached_response.json()["id"] == payload["id"]
    assert fake_tts.calls == 1


def test_generate_sentence_audio_validates_missing_sentence(
    client: TestClient,
    fake_tts: FakeTTSProvider,
) -> None:
    missing_sentence_id = uuid4()
    response = client.post(f"/api/audio/sentences/{missing_sentence_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == f"Sentence not found: {missing_sentence_id}"
    assert fake_tts.calls == 0


def test_generate_sentence_audio_marks_asset_failed_when_provider_fails(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _book, sentence = create_ready_book(db_session)
    failing_provider = FakeTTSProvider(should_fail=True)
    monkeypatch.setattr("app.services.audio.default_tts_provider", failing_provider)

    response = client.post(f"/api/audio/sentences/{sentence.id}")

    assert response.status_code == 502
    assert response.json()["detail"] == "TTS generation failed: fake provider failure"
    assert failing_provider.calls == 1

    [asset] = db_session.query(AudioAsset).all()
    assert asset.status == AudioStatus.FAILED.value
    assert asset.error_message == "fake provider failure"

    working_provider = FakeTTSProvider()
    monkeypatch.setattr("app.services.audio.default_tts_provider", working_provider)
    retry_response = client.post(f"/api/audio/sentences/{sentence.id}")

    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == AudioStatus.READY.value
    assert retry_response.json()["id"] == str(asset.id)
    assert working_provider.calls == 1


def test_prefetch_queues_pending_audio_and_status_reports_it(
    client: TestClient,
    db_session: Session,
    fake_tts: FakeTTSProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _book, sentence = create_ready_book(db_session)
    queued_sentence_ids: list[str] = []

    def fake_background_job(sentence_id):
        queued_sentence_ids.append(str(sentence_id))

    monkeypatch.setattr("app.api.routes.audio.generate_sentence_audio_job", fake_background_job)

    response = client.post(
        "/api/audio/sentences/prefetch",
        json={"sentence_ids": [str(sentence.id)]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["queued_sentence_ids"] == [str(sentence.id)]
    assert payload["assets"][0]["sentence_id"] == str(sentence.id)
    assert payload["assets"][0]["status"] == AudioStatus.PENDING.value
    assert payload["assets"][0]["audio_url"] is None
    assert queued_sentence_ids == [str(sentence.id)]
    assert fake_tts.calls == 0

    status_response = client.post(
        "/api/audio/sentences/status",
        json={"sentence_ids": [str(sentence.id)]},
    )

    assert status_response.status_code == 200
    assert status_response.json()[0]["status"] == AudioStatus.PENDING.value


def test_prefetch_and_status_validate_missing_sentence(
    client: TestClient,
    fake_tts: FakeTTSProvider,
) -> None:
    missing_sentence_id = uuid4()

    prefetch_response = client.post(
        "/api/audio/sentences/prefetch",
        json={"sentence_ids": [str(missing_sentence_id)]},
    )
    status_response = client.post(
        "/api/audio/sentences/status",
        json={"sentence_ids": [str(missing_sentence_id)]},
    )

    assert prefetch_response.status_code == 404
    assert prefetch_response.json()["detail"] == f"Sentence not found: {missing_sentence_id}"
    assert status_response.status_code == 404
    assert status_response.json()["detail"] == f"Sentence not found: {missing_sentence_id}"
    assert fake_tts.calls == 0


def test_audio_file_endpoint_rejects_unready_missing_and_outside_storage_assets(
    client: TestClient,
    db_session: Session,
    fake_tts: FakeTTSProvider,
    tmp_path: Path,
) -> None:
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

    pending_response = client.get(f"/api/audio/assets/{pending_asset.id}/file")
    assert pending_response.status_code == 409

    _book, missing_sentence = create_ready_book(db_session, title="Missing Audio File")
    missing_path_asset = make_audio_asset(
        db_session,
        missing_sentence,
        fake_tts,
        storage_path=str(settings.audio_dir / "missing.mp3"),
    )
    missing_response = client.get(f"/api/audio/assets/{missing_path_asset.id}/file")
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
    outside_response = client.get(f"/api/audio/assets/{outside_asset.id}/file")
    assert outside_response.status_code == 404

    not_found_response = client.get(f"/api/audio/assets/{uuid4()}/file")
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
