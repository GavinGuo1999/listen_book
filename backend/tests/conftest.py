from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.workers import jobs, parse_books


@pytest.fixture
def db_session(tmp_path, monkeypatch) -> Generator[Session, None, None]:
    storage_root = tmp_path / "storage"
    for directory in ("uploads", "parsed", "audio"):
        (storage_root / directory).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "storage_root", storage_root)
    for cached_name in ("uploads_dir", "parsed_dir", "audio_dir"):
        settings.__dict__.pop(cached_name, None)

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(parse_books, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(jobs, "SessionLocal", TestingSessionLocal)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
