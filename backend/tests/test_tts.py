from app.services.tts import EdgeTTSProvider


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
