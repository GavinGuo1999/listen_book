from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError

from e2e_env import BACKEND_DIR, REPO_ROOT, configure_e2e_environment, maintenance_database_url


def main() -> None:
    config = configure_e2e_environment()
    if make_url(config.database_url).get_backend_name() != "sqlite":
        _create_database_if_missing(config.source_database_url, config.database_name)
    _initialize_schema(config.database_url)
    _reset_e2e_data()
    print(f"e2e_database={config.database_name}")
    print(f"e2e_storage_root={config.storage_root}")
    print(f"e2e_admin_username={config.admin_username}")


def _create_database_if_missing(database_url: str, database_name: str) -> None:
    engine = create_engine(maintenance_database_url(database_url), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": database_name},
            )
            if exists:
                return
            try:
                connection.execute(text(f'CREATE DATABASE "{database_name}"'))
            except ProgrammingError as exc:
                raise RuntimeError(
                    "Could not create the E2E database automatically. "
                    "Create it once with a PostgreSQL admin account, then rerun E2E: "
                    f'CREATE DATABASE "{database_name}" OWNER listen_book_app;'
                ) from exc
    finally:
        engine.dispose()


def _initialize_schema(database_url: str) -> None:
    if make_url(database_url).get_backend_name() == "sqlite":
        from app.db.base import Base

        engine = create_engine(database_url)
        try:
            Base.metadata.create_all(engine)
        finally:
            engine.dispose()
        return

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(alembic_config, "head")


def _reset_e2e_data() -> None:
    from app.core.config import settings
    from app.db.base import Base
    from app.db.session import SessionLocal
    from app.services.auth import bootstrap_admin_user

    storage_root = settings.storage_root.resolve()
    expected_storage_root = (REPO_ROOT / "storage" / "e2e").resolve()
    if not storage_root.is_relative_to(expected_storage_root):
        raise RuntimeError(f"Refusing to reset non-E2E storage root: {storage_root}")

    db = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(delete(table))
        db.commit()

        if not settings.bootstrap_admin_username or not settings.bootstrap_admin_password:
            raise RuntimeError("E2E bootstrap admin env is not configured")

        bootstrap_admin_user(
            db,
            username=settings.bootstrap_admin_username,
            password=settings.bootstrap_admin_password,
        )
    finally:
        db.close()

    storage_root.mkdir(parents=True, exist_ok=True)
    database_url = make_url(settings.database_url)
    sqlite_database_path = (
        Path(database_url.database).resolve()
        if database_url.get_backend_name() == "sqlite" and database_url.database
        else None
    )
    for item in storage_root.rglob("*"):
        if sqlite_database_path is not None and item.resolve() == sqlite_database_path:
            continue
        if item.is_file() and item.name != ".gitkeep":
            item.unlink()
        elif item.is_dir() and not _contains_gitkeep(item):
            _remove_empty_directory(item)


def _contains_gitkeep(path: Path) -> bool:
    return any(child.name == ".gitkeep" for child in path.iterdir())


def _remove_empty_directory(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        pass


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
