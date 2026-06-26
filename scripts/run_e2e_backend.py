from __future__ import annotations

import uvicorn

from e2e_env import configure_e2e_environment


def main() -> None:
    config = configure_e2e_environment()
    uvicorn.run(
        "app.main:app",
        host=config.backend_host,
        port=config.backend_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
