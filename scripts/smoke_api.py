from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local API smoke test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=float, default=30.0, help="Seconds to wait for parsing")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    title = f"codex-smoke-{int(time.time())}"
    book_id: str | None = None

    with httpx.Client(base_url=base_url, timeout=10.0, trust_env=False) as client:
        health = client.get("/api/health")
        health.raise_for_status()

        upload = client.post(
            "/api/books",
            files={"file": (f"{title}.txt", "第一句。第二句。".encode("utf-8"), "text/plain")},
        )
        upload.raise_for_status()
        book_id = upload.json()["id"]

        book = wait_for_book_ready(client, book_id, args.timeout)
        print(f"book ready: {book['title']} ({book_id})")

        chapters = client.get(f"/api/books/{book_id}/chapters")
        chapters.raise_for_status()
        sentence = first_sentence(chapters.json())
        print(f"first sentence: {sentence['text']}")

        progress = client.put(
            f"/api/books/{book_id}/progress",
            json={"sentence_id": sentence["id"], "audio_position_ms": 1234},
        )
        progress.raise_for_status()

        loaded_progress = client.get(f"/api/books/{book_id}/progress")
        loaded_progress.raise_for_status()
        if loaded_progress.json()["audio_position_ms"] != 1234:
            raise RuntimeError("progress audio_position_ms was not persisted")
        print("progress persisted")

        delete = client.delete(f"/api/books/{book_id}")
        delete.raise_for_status()
        print("test book deleted")

    return 0


def wait_for_book_ready(client: httpx.Client, book_id: str, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status = "unknown"

    while time.monotonic() < deadline:
        books = client.get("/api/books")
        books.raise_for_status()
        for book in books.json():
            if book["id"] != book_id:
                continue
            last_status = book["status"]
            if last_status == "ready":
                return book
            if last_status == "failed":
                raise RuntimeError(f"book parsing failed: {book}")
        time.sleep(0.5)

    raise TimeoutError(f"book did not become ready within {timeout_seconds}s; last={last_status}")


def first_sentence(chapters: list[dict[str, Any]]) -> dict[str, Any]:
    for chapter in chapters:
        for paragraph in chapter["paragraphs"]:
            if paragraph["sentences"]:
                return paragraph["sentences"][0]
    raise RuntimeError("no sentence found in parsed book")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"smoke failed: {exc}", file=sys.stderr)
        raise
