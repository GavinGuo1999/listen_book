from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audio import AudioAsset, AudioStatus
from app.models.book import Sentence
from app.models.job import JobType
from app.services.jobs import enqueue_job
from app.services.tts import TTSRequest, default_tts_provider, select_voice_for_text

DEFAULT_SPEED = 100


def sentence_audio_stmt(sentence: Sentence):
    provider = default_tts_provider
    voice = select_voice_for_text(sentence.text)
    return select(AudioAsset).where(
        AudioAsset.sentence_id == sentence.id,
        AudioAsset.model_name == provider.model_name,
        AudioAsset.model_version == provider.model_version,
        AudioAsset.voice == voice,
        AudioAsset.speed == DEFAULT_SPEED,
        AudioAsset.text_hash == sentence.text_hash,
    )


def audio_file_is_available(asset: AudioAsset) -> bool:
    if asset.storage_path is None:
        return False
    path = Path(asset.storage_path)
    return path.is_file() and path.stat().st_size > 0


def get_existing_sentence_audio(db: Session, sentence: Sentence) -> AudioAsset | None:
    return db.scalar(sentence_audio_stmt(sentence))


def ensure_pending_sentence_audio(
    db: Session,
    sentence: Sentence,
    *,
    commit: bool = True,
) -> AudioAsset:
    existing = get_existing_sentence_audio(db, sentence)
    if existing is not None:
        return existing

    provider = default_tts_provider
    voice = select_voice_for_text(sentence.text)
    asset = AudioAsset(
        sentence_id=sentence.id,
        model_name=provider.model_name,
        model_version=provider.model_version,
        voice=voice,
        speed=DEFAULT_SPEED,
        text_hash=sentence.text_hash,
        status=AudioStatus.PENDING.value,
    )
    db.add(asset)
    if commit:
        db.commit()
        db.refresh(asset)
    else:
        db.flush()
    return asset


def queue_sentence_audio(db: Session, sentence: Sentence) -> tuple[AudioAsset, bool]:
    asset = get_existing_sentence_audio(db, sentence)
    if (
        asset is not None
        and asset.status == AudioStatus.READY.value
        and audio_file_is_available(asset)
    ):
        return asset, False

    asset = asset or ensure_pending_sentence_audio(db, sentence, commit=False)
    job, created = enqueue_job(
        db,
        job_type=JobType.GENERATE_AUDIO.value,
        payload={"sentence_id": str(sentence.id), "audio_asset_id": str(asset.id)},
        dedupe_key=f"audio:{asset.id}",
        priority=50,
    )
    if created or job.status == "pending":
        asset.status = AudioStatus.PENDING.value
        asset.error_message = None
    db.commit()
    db.refresh(asset)
    return asset, created


def generate_sentence_audio_asset(db: Session, sentence_id: UUID) -> AudioAsset:
    sentence = db.get(Sentence, sentence_id)
    if sentence is None:
        raise LookupError(f"Sentence not found: {sentence_id}")

    provider = default_tts_provider
    voice = select_voice_for_text(sentence.text)
    existing = get_existing_sentence_audio(db, sentence)
    if (
        existing is not None
        and existing.status == AudioStatus.READY.value
        and audio_file_is_available(existing)
    ):
        return existing

    asset = existing or AudioAsset(
        sentence_id=sentence.id,
        model_name=provider.model_name,
        model_version=provider.model_version,
        voice=voice,
        speed=DEFAULT_SPEED,
        text_hash=sentence.text_hash,
        status=AudioStatus.PENDING.value,
    )
    if existing is None:
        db.add(asset)

    asset.status = AudioStatus.GENERATING.value
    asset.error_message = None
    db.commit()
    db.refresh(asset)

    try:
        result = provider.generate(
            TTSRequest(text=sentence.text, voice=asset.voice, speed=asset.speed)
        )
    except Exception as exc:
        asset.status = AudioStatus.FAILED.value
        asset.error_message = str(exc)
        db.commit()
        raise RuntimeError(f"TTS generation failed: {exc}") from exc

    asset.storage_path = result.audio_path
    asset.duration_ms = result.duration_ms
    asset.status = AudioStatus.READY.value
    db.commit()
    db.refresh(asset)
    return asset
