from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
DATABASE_PATH = (REPO_ROOT / "storage" / "e2e" / "listen_book_e2e.db").resolve()


def main() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["LISTEN_BOOK_E2E_DATABASE_URL"] = (
        f"sqlite+pysqlite:///{DATABASE_PATH.as_posix()}"
    )
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    completed = subprocess.run(
        [npm, "run", "test:e2e"],
        cwd=FRONTEND_DIR,
        env=env,
        check=False,
    )
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
