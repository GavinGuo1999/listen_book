from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.book import Book
from app.models.operations import AdminAuditEvent, WorkerHeartbeat
from app.models.user import User


def list_admin_users(
    db: Session,
    *,
    query: str = "",
    status_filter: str = "all",
    role_filter: str = "all",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[User, int]], int]:
    conditions = []
    cleaned_query = query.strip()
    if cleaned_query:
        pattern = f"%{cleaned_query}%"
        conditions.append(
            or_(User.username.ilike(pattern), User.display_name.ilike(pattern))
        )
    if status_filter == "active":
        conditions.append(User.is_active.is_(True))
    elif status_filter == "disabled":
        conditions.append(User.is_active.is_(False))
    if role_filter == "admin":
        conditions.append(User.is_admin.is_(True))
    elif role_filter == "user":
        conditions.append(User.is_admin.is_(False))

    total = db.scalar(select(func.count(User.id)).where(*conditions)) or 0
    users = list(
        db.scalars(
            select(User)
            .where(*conditions)
            .order_by(User.created_at.desc(), User.username)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    if not users:
        return [], total

    upload_counts = dict(
        db.execute(
            select(Book.uploader_id, func.count(Book.id))
            .where(Book.uploader_id.in_([user.id for user in users]))
            .group_by(Book.uploader_id)
        ).all()
    )
    return [(user, upload_counts.get(user.id, 0)) for user in users], total


def update_admin_user(
    db: Session,
    user_id: UUID,
    *,
    actor: User,
    is_admin: bool | None,
    is_active: bool | None,
) -> User:
    if is_admin is None and is_active is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one user field must be provided",
        )

    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="不能修改当前登录账号的权限或状态",
        )

    bootstrap_username = (settings.bootstrap_admin_username or "").strip().lower()
    removing_bootstrap_access = (
        target.username == bootstrap_username
        and (is_admin is False or is_active is False)
    )
    if removing_bootstrap_access:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bootstrap 管理员由环境配置保护，不能停用或撤权",
        )

    next_is_admin = target.is_admin if is_admin is None else is_admin
    next_is_active = target.is_active if is_active is None else is_active
    removes_active_admin = (
        target.is_admin
        and target.is_active
        and (not next_is_admin or not next_is_active)
    )
    if removes_active_admin and _count_other_active_admins(db, target.id) == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="至少需要保留一个启用中的管理员",
        )

    if target.is_active != next_is_active:
        db.add(
            AdminAuditEvent(
                actor_id=actor.id,
                target_user_id=target.id,
                action="user_enabled" if next_is_active else "user_disabled",
                details={"from": target.is_active, "to": next_is_active},
            )
        )
        target.is_active = next_is_active
    if target.is_admin != next_is_admin:
        db.add(
            AdminAuditEvent(
                actor_id=actor.id,
                target_user_id=target.id,
                action="admin_granted" if next_is_admin else "admin_revoked",
                details={"from": target.is_admin, "to": next_is_admin},
            )
        )
        target.is_admin = next_is_admin

    db.commit()
    db.refresh(target)
    return target


def list_admin_audit_events(db: Session, *, limit: int = 100) -> list[AdminAuditEvent]:
    return list(
        db.scalars(
            select(AdminAuditEvent)
            .options(
                selectinload(AdminAuditEvent.actor),
                selectinload(AdminAuditEvent.target_user),
            )
            .order_by(AdminAuditEvent.created_at.desc())
            .limit(limit)
        ).all()
    )


def record_worker_heartbeat(
    db: Session,
    *,
    worker_id: str,
    hostname: str,
    process_id: int,
    started_at: datetime,
    now: datetime | None = None,
) -> WorkerHeartbeat:
    now = now or datetime.now(UTC)
    heartbeat = db.get(WorkerHeartbeat, worker_id)
    if heartbeat is None:
        heartbeat = WorkerHeartbeat(
            worker_id=worker_id,
            hostname=hostname,
            process_id=process_id,
            started_at=started_at,
            last_seen_at=now,
        )
        db.add(heartbeat)
    else:
        heartbeat.hostname = hostname
        heartbeat.process_id = process_id
        heartbeat.last_seen_at = now

    db.execute(
        delete(WorkerHeartbeat).where(
            WorkerHeartbeat.worker_id != worker_id,
            WorkerHeartbeat.last_seen_at < now - timedelta(days=7),
        )
    )
    db.commit()
    return heartbeat


def list_worker_heartbeats(db: Session) -> list[WorkerHeartbeat]:
    return list(
        db.scalars(
            select(WorkerHeartbeat).order_by(WorkerHeartbeat.last_seen_at.desc())
        ).all()
    )


def _count_other_active_admins(db: Session, excluded_user_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count(User.id)).where(
                User.id != excluded_user_id,
                User.is_admin.is_(True),
                User.is_active.is_(True),
            )
        )
        or 0
    )
