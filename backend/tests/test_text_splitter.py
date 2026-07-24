import json
from pathlib import Path

import pytest

from app.services.text_splitter import split_paragraphs, split_sentences

GOLDEN_CASES_PATH = (
    Path(__file__).resolve().parents[2] / "samples" / "sentence_splitter_golden" / "cases.json"
)


def load_golden_cases() -> list[dict[str, object]]:
    payload = json.loads(GOLDEN_CASES_PATH.read_text(encoding="utf-8"))
    return payload["cases"]


@pytest.mark.parametrize(
    "case",
    load_golden_cases(),
    ids=lambda case: str(case["id"]),
)
def test_sentence_splitter_golden_cases(case: dict[str, object]) -> None:
    assert split_sentences(str(case["input"])) == case["expected"]


def test_split_paragraphs_normalizes_blank_lines_and_whitespace() -> None:
    assert split_paragraphs(" 第一段。\r\n\r\n  第二段。 \n\n") == ["第一段。", "第二段。"]
