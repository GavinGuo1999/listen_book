import json
from pathlib import Path

import pytest

from app.services.tts import (
    CHINESE_VOICE,
    ENGLISH_VOICE,
    EdgeTTSProvider,
    build_tts_segments,
    normalize_spoken_text,
    select_voice_for_text,
)

GOLDEN_CASES_PATH = Path(__file__).resolve().parents[2] / "samples" / "tts_golden" / "cases.json"


def load_golden_cases() -> list[dict[str, object]]:
    payload = json.loads(GOLDEN_CASES_PATH.read_text(encoding="utf-8"))
    return payload["cases"]


@pytest.mark.parametrize(
    "case",
    load_golden_cases(),
    ids=lambda case: str(case["id"]),
)
def test_tts_golden_voice_and_prosody(case: dict[str, object]) -> None:
    provider = EdgeTTSProvider()
    text = str(case["text"])
    speed = int(case["speed"])

    assert select_voice_for_text(text) == case["expected_voice"]
    assert provider.infer_prosody(text, speed) == (
        case["expected_rate"],
        case["expected_pitch"],
    )
    if "expected_segments" in case:
        assert [
            {"text": segment.text, "voice": segment.voice}
            for segment in build_tts_segments(text, str(case["expected_voice"]))
        ] == case["expected_segments"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("那一行。", "那一航。"),
        ("这一行写错了。", "这一航写错了。"),
        ("请看第 12 行。", "请看第 12 航。"),
        ("银行门口。", "银行门口。"),
        ("他一行人出发了。", "他一行人出发了。"),
        ("这一行动很及时。", "这一行动很及时。"),
    ],
)
def test_normalize_spoken_text_handles_line_measure_word(
    text: str,
    expected: str,
) -> None:
    assert normalize_spoken_text(text) == expected


def test_build_tts_segments_switches_only_quoted_english() -> None:
    segments = build_tts_segments(
        "她说：“The End.”然后合上书。",
        CHINESE_VOICE,
    )

    assert [(segment.text, segment.voice) for segment in segments] == [
        ("她说：", CHINESE_VOICE),
        ("The End.", ENGLISH_VOICE),
        ("然后合上书。", CHINESE_VOICE),
    ]


def test_infer_prosody_keeps_plain_questions_neutral() -> None:
    provider = EdgeTTSProvider()

    assert provider.infer_prosody("你今天去书房吗？", 100) == ("+0%", "+0Hz")


def test_infer_prosody_distinguishes_dialogue_from_narration() -> None:
    provider = EdgeTTSProvider()

    assert provider.infer_prosody("“我马上回来。”", 100) == ("+2%", "+4Hz")


def test_infer_prosody_slows_long_comma_rich_narration() -> None:
    provider = EdgeTTSProvider()

    rate, pitch = provider.infer_prosody(
        "夜色渐渐深了，风从窗缝里吹进来，灯影在墙上摇晃，屋里的人都沉默着，又过了许久，谁也没有先开口。",
        100,
    )

    assert rate == "-7%"
    assert pitch == "+0Hz"


def test_infer_prosody_marks_soft_and_strong_speech() -> None:
    provider = EdgeTTSProvider()

    assert provider.infer_prosody("她低声说道：“别惊动他们。”", 100) == ("-3%", "-4Hz")
    assert provider.infer_prosody("他大声喊道：“快走！”", 100) == ("+11%", "+12Hz")


def test_infer_prosody_slows_ellipsis_more_than_regular_sentence() -> None:
    provider = EdgeTTSProvider()

    assert provider.infer_prosody("他望着远处，半天没有说话……", 100) == ("-8%", "-6Hz")
