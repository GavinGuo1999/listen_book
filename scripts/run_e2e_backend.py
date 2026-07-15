from __future__ import annotations

import threading

import uvicorn

from e2e_env import configure_e2e_environment


def main() -> None:
    config = configure_e2e_environment()
    from app.workers.jobs import run_forever

    stop_event = threading.Event()
    worker = threading.Thread(
        target=run_forever,
        args=(stop_event,),
        name="listen-book-e2e-worker",
        daemon=True,
    )
    worker.start()
    try:
        uvicorn.run(
            "app.main:app",
            host=config.backend_host,
            port=config.backend_port,
            log_level="info",
        )
    finally:
        stop_event.set()
        worker.join(timeout=5)


if __name__ == "__main__":
    main()
