from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.services.system import read_system_status  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with SessionLocal() as db:
        result = read_system_status(db)
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 1 if result.status == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
