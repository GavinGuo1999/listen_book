import argparse
import hashlib
import html
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
DEFAULT_CASES_PATH = ROOT_DIR / "samples" / "tts_golden" / "cases.json"
DEFAULT_OUTPUT_ROOT = ROOT_DIR / "storage" / "audio" / "tts_golden"

sys.path.insert(0, str(BACKEND_DIR))

from app.services.tts import (  # noqa: E402
    EdgeTTSProvider,
    TTSRequest,
    build_tts_segments,
    select_voice_for_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic Listen Book TTS audition samples."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--case",
        action="append",
        dest="case_ids",
        help="Generate only this case id. May be provided more than once.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace MP3 files that already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the suite without network calls or file writes.",
    )
    return parser.parse_args()


def load_suite(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("TTS golden suite must contain at least one case")

    case_ids = [case.get("id") for case in cases]
    if any(not isinstance(case_id, str) or not case_id for case_id in case_ids):
        raise ValueError("Every TTS golden case must have a non-empty id")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("TTS golden case ids must be unique")
    return payload


def select_cases(suite: dict[str, Any], case_ids: list[str] | None) -> list[dict[str, Any]]:
    cases = suite["cases"]
    if not case_ids:
        return cases

    requested = set(case_ids)
    available = {case["id"] for case in cases}
    missing = sorted(requested - available)
    if missing:
        raise ValueError(f"Unknown TTS golden case ids: {', '.join(missing)}")
    return [case for case in cases if case["id"] in requested]


def validate_case(provider: EdgeTTSProvider, case: dict[str, Any]) -> tuple[str, str, str]:
    text = str(case["text"])
    speed = int(case["speed"])
    voice = select_voice_for_text(text)
    rate, pitch = provider.infer_prosody(text, speed)
    actual = (voice, rate, pitch)
    expected = (
        case["expected_voice"],
        case["expected_rate"],
        case["expected_pitch"],
    )
    if actual != expected:
        raise ValueError(f"{case['id']} expected {expected}, inferred {actual}")
    segments = [
        {"text": segment.text, "voice": segment.voice}
        for segment in build_tts_segments(text, voice)
    ]
    if "expected_segments" in case and segments != case["expected_segments"]:
        raise ValueError(
            f"{case['id']} expected segments {case['expected_segments']}, inferred {segments}"
        )
    return actual


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_case(
    provider: EdgeTTSProvider,
    case: dict[str, Any],
    output_dir: Path,
    *,
    force: bool,
) -> dict[str, Any]:
    voice, rate, pitch = validate_case(provider, case)
    destination = output_dir / f"{case['id']}.mp3"
    generated = force or not destination.is_file() or destination.stat().st_size == 0
    if generated:
        result = provider.generate(
            TTSRequest(text=str(case["text"]), voice=voice, speed=int(case["speed"]))
        )
        source = Path(result.audio_path)
        destination.unlink(missing_ok=True)
        shutil.move(str(source), destination)

    return {
        "id": case["id"],
        "language": case["language"],
        "category": case["category"],
        "text": case["text"],
        "voice": voice,
        "speed": case["speed"],
        "rate": rate,
        "pitch": pitch,
        "segments": [
            {"text": segment.text, "voice": segment.voice}
            for segment in build_tts_segments(str(case["text"]), voice)
        ],
        "audio_file": destination.name,
        "size_bytes": destination.stat().st_size,
        "sha256": file_sha256(destination),
        "generated": generated,
    }


def render_index(report: dict[str, Any]) -> str:
    rows = []
    for case in report["cases"]:
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(case['id'])}</strong><br>"
            f"<span>{html.escape(case['language'])} / {html.escape(case['category'])}</span></td>"
            f"<td>{html.escape(case['text'])}</td>"
            f"<td>{html.escape(' → '.join(segment['voice'] for segment in case['segments']))}<br>"
            f"{html.escape(case['rate'])} / {html.escape(case['pitch'])}</td>"
            f'<td><audio controls preload="none" src="{html.escape(case["audio_file"])}"></audio></td>'
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Listen Book TTS Golden - {html.escape(report["suite_version"])}</title>
  <style>
    body {{ margin: 0; color: #1d242b; background: #f4f6f7; font: 14px/1.5 system-ui; }}
    main {{ width: min(1180px, calc(100% - 32px)); margin: 32px auto; }}
    h1 {{ margin: 0 0 4px; font-size: 24px; }}
    p {{ margin: 0 0 20px; color: #58636d; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ padding: 12px; border: 1px solid #dce1e4; text-align: left; vertical-align: top; }}
    th {{ background: #eef1f2; }}
    td:first-child {{ width: 190px; }}
    td:nth-child(3) {{ width: 210px; }}
    td:last-child {{ width: 310px; }}
    span {{ color: #68737d; }}
    audio {{ width: 300px; max-width: 100%; }}
    @media (max-width: 760px) {{
      table, tbody, tr, td {{ display: block; }}
      thead {{ display: none; }}
      tr {{ border: 1px solid #dce1e4; margin-bottom: 12px; background: #fff; }}
      td, td:first-child, td:nth-child(3), td:last-child {{ width: auto; border: 0; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>TTS Golden {html.escape(report["suite_version"])}</h1>
    <p>模型 {html.escape(report["model_name"])} {html.escape(report["model_version"])}</p>
    <table>
      <thead><tr><th>样例</th><th>文本</th><th>参数</th><th>试听</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    suite = load_suite(args.cases.resolve())
    cases = select_cases(suite, args.case_ids)
    provider = EdgeTTSProvider()

    if args.dry_run:
        preview = []
        for case in cases:
            voice, rate, pitch = validate_case(provider, case)
            preview.append(
                {
                    "id": case["id"],
                    "voice": voice,
                    "speed": case["speed"],
                    "rate": rate,
                    "pitch": pitch,
                    "segments": [
                        {"text": segment.text, "voice": segment.voice}
                        for segment in build_tts_segments(str(case["text"]), voice)
                    ],
                }
            )
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    output_dir = args.output_root.resolve() / str(suite["suite_version"])
    output_dir.mkdir(parents=True, exist_ok=True)
    results = [
        generate_case(provider, case, output_dir, force=args.force)
        for case in cases
    ]
    report = {
        "suite_version": suite["suite_version"],
        "generated_at": datetime.now(UTC).isoformat(),
        "model_name": provider.model_name,
        "model_version": provider.model_version,
        "cases": results,
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "index.html").write_text(render_index(report), encoding="utf-8")
    print(output_dir / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
