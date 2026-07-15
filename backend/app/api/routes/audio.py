from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.audio import AudioAsset, AudioStatus
from app.models.book import Paragraph, Sentence
from app.models.job import JobType
from app.models.user import User
from app.schemas.audio import AudioAssetRead, AudioPrefetchRequest, AudioPrefetchResponse
from app.services.audio import (
    audio_file_is_available,
    ensure_pending_sentence_audio,
    get_existing_sentence_audio,
    queue_sentence_audio,
)
from app.services.books import ensure_chapter_accessible, ensure_sentence_accessible
from app.services.jobs import enqueue_job

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def to_audio_asset_read(asset: AudioAsset) -> AudioAssetRead:
    audio_url = (
        f"/api/audio/assets/{asset.id}/file"
        if asset.status == AudioStatus.READY.value and audio_file_is_available(asset)
        else None
    )
    return AudioAssetRead(
        id=asset.id,
        sentence_id=asset.sentence_id,
        status=asset.status,
        audio_url=audio_url,
        duration_ms=asset.duration_ms,
    )


@router.post("/sentences/prefetch", response_model=AudioPrefetchResponse)
def prefetch_sentence_audio(
    payload: AudioPrefetchRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> AudioPrefetchResponse:
    assets: list[AudioAssetRead] = []
    queued_sentence_ids: list[UUID] = []

    for sentence_id in payload.sentence_ids:
        sentence = ensure_sentence_accessible(db, sentence_id, current_user)

        asset, queued = queue_sentence_audio(db, sentence)
        if queued:
            queued_sentence_ids.append(sentence.id)

        assets.append(to_audio_asset_read(asset))

    return AudioPrefetchResponse(assets=assets, queued_sentence_ids=queued_sentence_ids)


@router.post("/sentences/status", response_model=list[AudioAssetRead])
def get_sentence_audio_statuses(
    payload: AudioPrefetchRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> list[AudioAssetRead]:
    assets: list[AudioAssetRead] = []

    for sentence_id in payload.sentence_ids:
        sentence = ensure_sentence_accessible(db, sentence_id, current_user)

        existing = get_existing_sentence_audio(db, sentence)
        if existing is not None:
            assets.append(to_audio_asset_read(existing))

    return assets


@router.post("/sentences/{sentence_id}", response_model=AudioAssetRead)
def generate_sentence_audio(
    sentence_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AudioAssetRead:
    sentence = ensure_sentence_accessible(db, sentence_id, current_user)
    asset, _queued = queue_sentence_audio(db, sentence)
    return to_audio_asset_read(asset)


@router.post("/chapters/{chapter_id}/prefetch", response_model=AudioPrefetchResponse)
def prefetch_chapter_audio(
    chapter_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AudioPrefetchResponse:
    ensure_chapter_accessible(db, chapter_id, current_user)
    sentences = list(
        db.scalars(
            select(Sentence)
            .join(Paragraph, Sentence.paragraph_id == Paragraph.id)
            .where(Paragraph.chapter_id == chapter_id)
            .order_by(Paragraph.paragraph_index, Sentence.sentence_index)
        ).all()
    )
    assets: list[AudioAsset] = []
    queued_sentence_ids: list[UUID] = []
    for sentence in sentences:
        existing = get_existing_sentence_audio(db, sentence)
        if (
            existing is not None
            and existing.status == AudioStatus.READY.value
            and audio_file_is_available(existing)
        ):
            assets.append(existing)
            continue
        asset = existing or ensure_pending_sentence_audio(db, sentence, commit=False)
        if asset.status not in {AudioStatus.PENDING.value, AudioStatus.GENERATING.value}:
            asset.status = AudioStatus.PENDING.value
            asset.error_message = None
        assets.append(asset)
        queued_sentence_ids.append(sentence.id)

    enqueue_job(
        db,
        job_type=JobType.PREFETCH_CHAPTER_AUDIO.value,
        payload={"chapter_id": str(chapter_id)},
        dedupe_key=f"prefetch:{chapter_id}",
        priority=40,
    )
    db.commit()
    return AudioPrefetchResponse(
        assets=[to_audio_asset_read(asset) for asset in assets],
        queued_sentence_ids=queued_sentence_ids,
    )


@router.get("/assets/{asset_id}/file")
def get_audio_file(asset_id: UUID, db: DbSession, current_user: CurrentUser) -> FileResponse:
    asset = db.get(AudioAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio asset not found")
    ensure_sentence_accessible(db, asset.sentence_id, current_user)
    if asset.status != AudioStatus.READY.value or asset.storage_path is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Audio asset is not ready")

    audio_path = Path(asset.storage_path).resolve()
    audio_root = settings.audio_dir.resolve()
    if not audio_path.is_file() or not audio_path.is_relative_to(audio_root):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

    media_type = "audio/mpeg" if audio_path.suffix.lower() == ".mp3" else "audio/wav"
    return FileResponse(audio_path, media_type=media_type, filename=audio_path.name)
