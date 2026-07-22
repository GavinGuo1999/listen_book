from functools import cached_property
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="LISTEN_BOOK_",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://listen_book_app:change-me@localhost:5432/listen_book"
    secret_key: str = "change-me-in-development"
    session_cookie_name: str = "listen_book_session"
    session_cookie_secure: bool = False
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None
    storage_root: Path = Field(default=PROJECT_ROOT / "storage")
    job_retention_days: int = Field(default=30, ge=1)
    job_cleanup_interval_seconds: int = Field(default=3600, ge=60)
    worker_heartbeat_interval_seconds: int = Field(default=5, ge=1)
    worker_offline_after_seconds: int = Field(default=30, ge=5)
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="LISTEN_BOOK_CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    @cached_property
    def uploads_dir(self) -> Path:
        return self.storage_root / "uploads"

    @cached_property
    def parsed_dir(self) -> Path:
        return self.storage_root / "parsed"

    @cached_property
    def audio_dir(self) -> Path:
        return self.storage_root / "audio"

    def ensure_storage_dirs(self) -> None:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
