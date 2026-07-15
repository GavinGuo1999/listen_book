from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL, make_url

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://listen_book_app:change-me@localhost:5432/listen_book"
)
DEFAULT_E2E_DATABASE_NAME = "listen_book_e2e"
DEFAULT_E2E_ADMIN_USERNAME = "admin"
DEFAULT_E2E_ADMIN_PASSWORD = "e2e-admin-password"
DATABASE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
E2E_DATABASE_URL_KEY = "LISTEN_BOOK_E2E_DATABASE_URL"


@dataclass(frozen=True)
class E2EConfig:
    source_database_url: str
    database_url: str
    database_name: str
    storage_root: Path
    admin_username: str
    admin_password: str
    backend_host: str
    backend_port: int


def configure_e2e_environment() -> E2EConfig:
    base_database_url = _read_config_value("LISTEN_BOOK_DATABASE_URL", DEFAULT_DATABASE_URL)
    database_name = os.environ.get("LISTEN_BOOK_E2E_DATABASE_NAME", DEFAULT_E2E_DATABASE_NAME)
    if not DATABASE_NAME_PATTERN.fullmatch(database_name):
        raise RuntimeError(f"Unsafe E2E database name: {database_name}")
    storage_root = Path(
        os.environ.get("LISTEN_BOOK_E2E_STORAGE_ROOT", REPO_ROOT / "storage" / "e2e")
    ).resolve()
    database_url_override = os.environ.get(E2E_DATABASE_URL_KEY)
    if database_url_override:
        database_url = _validate_database_url_override(database_url_override, storage_root)
    else:
        database_url = make_url(base_database_url).set(database=database_name).render_as_string(
            hide_password=False
        )
    admin_username = os.environ.get(
        "LISTEN_BOOK_E2E_ADMIN_USERNAME",
        DEFAULT_E2E_ADMIN_USERNAME,
    )
    admin_password = os.environ.get(
        "LISTEN_BOOK_E2E_ADMIN_PASSWORD",
        DEFAULT_E2E_ADMIN_PASSWORD,
    )
    backend_host = os.environ.get("LISTEN_BOOK_E2E_BACKEND_HOST", "127.0.0.1")
    backend_port = int(os.environ.get("LISTEN_BOOK_E2E_BACKEND_PORT", "8001"))

    os.environ["LISTEN_BOOK_DATABASE_URL"] = database_url
    os.environ["LISTEN_BOOK_STORAGE_ROOT"] = str(storage_root)
    os.environ["LISTEN_BOOK_BOOTSTRAP_ADMIN_USERNAME"] = admin_username
    os.environ["LISTEN_BOOK_BOOTSTRAP_ADMIN_PASSWORD"] = admin_password
    os.environ["LISTEN_BOOK_CORS_ORIGINS"] = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )

    backend_path = str(BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    return E2EConfig(
        source_database_url=base_database_url,
        database_url=database_url,
        database_name=database_name,
        storage_root=storage_root,
        admin_username=admin_username,
        admin_password=admin_password,
        backend_host=backend_host,
        backend_port=backend_port,
    )


def maintenance_database_url(source_database_url: str) -> URL:
    return make_url(source_database_url)


def _validate_database_url_override(database_url: str, storage_root: Path) -> str:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        if url.database != DEFAULT_E2E_DATABASE_NAME:
            raise RuntimeError(
                f"{E2E_DATABASE_URL_KEY} must target {DEFAULT_E2E_DATABASE_NAME!r}"
            )
        return url.render_as_string(hide_password=False)

    if not url.database or url.database == ":memory:":
        raise RuntimeError(f"{E2E_DATABASE_URL_KEY} must use a file under storage/e2e")
    database_path = Path(url.database)
    if not database_path.is_absolute():
        database_path = (REPO_ROOT / database_path).resolve()
    else:
        database_path = database_path.resolve()
    if not database_path.is_relative_to(storage_root):
        raise RuntimeError(f"Refusing E2E SQLite database outside {storage_root}")
    return f"sqlite+pysqlite:///{database_path.as_posix()}"


def _read_config_value(key: str, default: str) -> str:
    if value := os.environ.get(key):
        return value

    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return default

    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        current_key, value = stripped.split("=", maxsplit=1)
        if current_key == key:
            return value

    return default
