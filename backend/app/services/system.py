from __future__ import annotations

from datetime import UTC, datetime, timedelta
from tempfile import NamedTemporaryFile

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, settings
from app.models.user import User
from app.schemas.admin import (
    SystemCheckRead,
    SystemStatusRead,
    WorkerStatusRead,
)
from app.services.operations import list_worker_heartbeats
from app.version import __version__

DEFAULT_SECRET_KEYS = {"change-me-in-development", "change-me"}
DEFAULT_ADMIN_PASSWORDS = {"change-me-admin-password", "change-me"}


def read_system_status(db: Session, *, now: datetime | None = None) -> SystemStatusRead:
    now = now or datetime.now(UTC)
    checks: list[SystemCheckRead] = []

    database_ok = _check_database(db, checks)
    if database_ok:
        _check_migrations(db, checks)
        _check_admin_account(db, checks)
    else:
        checks.append(
            _check("migrations", "数据库迁移", "error", "数据库不可用，无法检查迁移版本")
        )
        checks.append(
            _check("admin", "管理员账号", "error", "数据库不可用，无法检查管理员账号")
        )

    _check_storage(checks)
    _check_secret_key(checks)
    _check_admin_password(checks)
    workers = _check_workers(db, checks, now=now) if database_ok else []

    overall_status = "ok"
    if any(item.status == "error" for item in checks):
        overall_status = "error"
    elif any(item.status == "warning" for item in checks):
        overall_status = "warning"

    return SystemStatusRead(
        status=overall_status,
        version=__version__,
        checked_at=now,
        checks=checks,
        workers=workers,
    )


def _check_database(db: Session, checks: list[SystemCheckRead]) -> bool:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db.rollback()
        checks.append(_check("database", "数据库连接", "error", type(exc).__name__))
        return False
    checks.append(_check("database", "数据库连接", "ok", "连接正常"))
    return True


def _check_migrations(db: Session, checks: list[SystemCheckRead]) -> None:
    try:
        current_revision = MigrationContext.configure(db.connection()).get_current_revision()
        alembic_config = Config()
        alembic_config.set_main_option(
            "script_location",
            str(PROJECT_ROOT / "backend" / "alembic"),
        )
        head_revision = ScriptDirectory.from_config(alembic_config).get_current_head()
    except Exception as exc:
        checks.append(_check("migrations", "数据库迁移", "error", type(exc).__name__))
        return

    if current_revision == head_revision:
        checks.append(_check("migrations", "数据库迁移", "ok", f"已在 {head_revision}"))
    elif current_revision is None and db.bind is not None and db.bind.dialect.name == "sqlite":
        checks.append(
            _check("migrations", "数据库迁移", "warning", "SQLite 测试库未记录 Alembic 版本")
        )
    else:
        checks.append(
            _check(
                "migrations",
                "数据库迁移",
                "error",
                f"当前 {current_revision or '未记录'}，期望 {head_revision}",
            )
        )


def _check_admin_account(db: Session, checks: list[SystemCheckRead]) -> None:
    active_admins = db.scalar(
        select(func.count(User.id)).where(
            User.is_admin.is_(True),
            User.is_active.is_(True),
        )
    )
    if active_admins:
        checks.append(_check("admin", "管理员账号", "ok", f"{active_admins} 个启用中的管理员"))
    else:
        checks.append(_check("admin", "管理员账号", "error", "没有启用中的管理员"))


def _check_storage(checks: list[SystemCheckRead]) -> None:
    try:
        settings.ensure_storage_dirs()
        with NamedTemporaryFile(
            dir=settings.storage_root,
            prefix=".listen-book-check-",
            delete=True,
        ):
            pass
    except OSError as exc:
        checks.append(_check("storage", "存储目录", "error", type(exc).__name__))
        return
    checks.append(_check("storage", "存储目录", "ok", "目录存在且可写"))


def _check_secret_key(checks: list[SystemCheckRead]) -> None:
    secret_key = settings.secret_key.strip()
    if secret_key in DEFAULT_SECRET_KEYS or len(secret_key) < 32:
        checks.append(
            _check("secret_key", "会话密钥", "warning", "仍为默认值或长度不足 32 位")
        )
    else:
        checks.append(_check("secret_key", "会话密钥", "ok", "已配置非默认密钥"))


def _check_admin_password(checks: list[SystemCheckRead]) -> None:
    password = settings.bootstrap_admin_password
    if not settings.bootstrap_admin_username or not password:
        checks.append(
            _check("admin_password", "管理员启动配置", "warning", "未配置 bootstrap 管理员")
        )
    elif password in DEFAULT_ADMIN_PASSWORDS:
        checks.append(
            _check("admin_password", "管理员启动配置", "warning", "仍在使用示例管理员密码")
        )
    else:
        checks.append(
            _check("admin_password", "管理员启动配置", "ok", "已配置非示例管理员密码")
        )


def _check_workers(
    db: Session,
    checks: list[SystemCheckRead],
    *,
    now: datetime,
) -> list[WorkerStatusRead]:
    cutoff = now - timedelta(seconds=settings.worker_offline_after_seconds)
    workers = []
    for heartbeat in list_worker_heartbeats(db):
        last_seen_at = _as_utc(heartbeat.last_seen_at)
        workers.append(
            WorkerStatusRead(
                worker_id=heartbeat.worker_id,
                hostname=heartbeat.hostname,
                process_id=heartbeat.process_id,
                started_at=_as_utc(heartbeat.started_at),
                last_seen_at=last_seen_at,
                is_online=last_seen_at >= cutoff,
            )
        )

    online_count = sum(worker.is_online for worker in workers)
    if online_count:
        checks.append(_check("worker", "后台 Worker", "ok", f"{online_count} 个在线 Worker"))
    elif workers:
        checks.append(_check("worker", "后台 Worker", "error", "Worker 心跳已超时"))
    else:
        checks.append(_check("worker", "后台 Worker", "error", "尚未收到 Worker 心跳"))
    return workers


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _check(key: str, label: str, status: str, message: str) -> SystemCheckRead:
    return SystemCheckRead(key=key, label=label, status=status, message=message)
