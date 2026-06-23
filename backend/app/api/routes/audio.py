from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.audio import AudioAsset, AudioStatus
from app.models.user import User
from app.schemas.audio import AudioAssetRead, AudioPrefetchRequest, AudioPrefetchResponse
from app.services.audio import (
    audio_asset_should_be_queued,
    audio_file_is_available,
    ensure_pending_sentence_audio,
    generate_sentence_audio_job,
    get_existing_sentence_audio,
    get_or_create_sentence_audio,
)
from app.services.books import ensure_sentence_accessible

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
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
) -> AudioPrefetchResponse:
    assets: list[AudioAssetRead] = []
    queued_sentence_ids: list[UUID] = []

    for sentence_id in payload.sentence_ids:
        sentence = ensure_sentence_accessible(db, sentence_id, current_user)

        existing = get_existing_sentence_audio(db, sentence)
        should_queue = existing is None or audio_asset_should_be_queued(existing)
        asset = existing or ensure_pending_sentence_audio(db, sentence)

        if should_queue:
            background_tasks.add_task(generate_sentence_audio_job, sentence.id)
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
    ensure_sentence_accessible(db, sentence_id, current_user)
    asset = get_or_create_sentence_audio(db, sentence_id)
    return to_audio_asset_read(asset)


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
