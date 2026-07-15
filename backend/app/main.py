from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.auth import bootstrap_admin_user


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    del app
    bootstrap_configured_admin()
    yield


def create_app() -> FastAPI:
    settings.ensure_storage_dirs()
    app = FastAPI(title="Listen Book API", version="0.4.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "name": "Listen Book API",
            "health": "/api/health",
            "docs": "/docs",
        }

    return app


def bootstrap_configured_admin() -> None:
    if not settings.bootstrap_admin_username or not settings.bootstrap_admin_password:
        return
    db = SessionLocal()
    try:
        bootstrap_admin_user(
            db,
            username=settings.bootstrap_admin_username,
            password=settings.bootstrap_admin_password,
        )
    finally:
        db.close()


app = create_app()
