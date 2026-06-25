from sqlalchemy import delete

from app.core.config import PROJECT_ROOT, settings
from app.db.base import Base
from app.db.session import SessionLocal
from app.services.auth import bootstrap_admin_user


def main() -> None:
    storage_root = settings.storage_root.resolve()
    project_root = PROJECT_ROOT.resolve()
    if not (storage_root == project_root / "storage" or storage_root.is_relative_to(project_root)):
        raise RuntimeError(f"Unsafe storage root: {storage_root}")

    db = SessionLocal()
    deleted_rows: dict[str, int | None] = {}
    try:
        for table in reversed(Base.metadata.sorted_tables):
            result = db.execute(delete(table))
            deleted_rows[table.name] = result.rowcount
        db.commit()

        if not settings.bootstrap_admin_username or not settings.bootstrap_admin_password:
            raise RuntimeError("Bootstrap admin env is not configured")

        admin = bootstrap_admin_user(
            db,
            username=settings.bootstrap_admin_username,
            password=settings.bootstrap_admin_password,
        )
    finally:
        db.close()

    removed_files = 0
    for dirname in ("uploads", "parsed", "audio"):
        directory = (storage_root / dirname).resolve()
        if not directory.is_relative_to(storage_root):
            raise RuntimeError(f"Unsafe storage directory: {directory}")
        directory.mkdir(parents=True, exist_ok=True)
        for item in directory.rglob("*"):
            if item.is_file() and item.name != ".gitkeep":
                item.unlink()
                removed_files += 1

    deleted_summary = ",".join(
        f"{table_name}:{row_count}" for table_name, row_count in deleted_rows.items()
    )
    print(f"deleted_tables={deleted_summary}")
    print(f"storage_files_removed={removed_files}")
    print(f"admin_username={admin.username}")


if __name__ == "__main__":
    main()
