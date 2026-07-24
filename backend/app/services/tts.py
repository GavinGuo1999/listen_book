import asyncio
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.config import settings

CHINESE_VOICE = "zh-CN-XiaoxiaoNeural"
ENGLISH_VOICE = "en-US-JennyNeural"
QUOTED_ENGLISH_RE = re.compile(
    r"""(?P<open>["“])\s*(?P<text>[A-Za-z][A-Za-z0-9 .,!?'":;\-]*?)\s*(?P<close>["”])"""
)
LINE_MEASURE_RE = re.compile(
    r"(?P<prefix>(?:第\s*[0-9一二三四五六七八九十百千两]+\s*|[这那哪每]一))"
    r"行(?!动)"
)


@dataclass(frozen=True)
class TTSRequest:
    text: str
    voice: str = CHINESE_VOICE
    speed: int = 100


@dataclass(frozen=True)
class TTSResult:
    audio_path: str
    duration_ms: int | None = None


@dataclass(frozen=True)
class TTSSegment:
    text: str
    voice: str


def normalize_spoken_text(text: str) -> str:
    return LINE_MEASURE_RE.sub(lambda match: f"{match.group('prefix')}航", text)


def build_tts_segments(text: str, default_voice: str) -> tuple[TTSSegment, ...]:
    if default_voice != CHINESE_VOICE or not any("\u3400" <= char <= "\u9fff" for char in text):
        return (TTSSegment(text=normalize_spoken_text(text), voice=default_voice),)

    segments: list[TTSSegment] = []
    start = 0
    for match in QUOTED_ENGLISH_RE.finditer(text):
        chinese_text = normalize_spoken_text(text[start : match.start()]).strip()
        if chinese_text:
            segments.append(TTSSegment(text=chinese_text, voice=CHINESE_VOICE))
        segments.append(TTSSegment(text=match.group("text").strip(), voice=ENGLISH_VOICE))
        start = match.end()

    chinese_tail = normalize_spoken_text(text[start:]).strip()
    if chinese_tail:
        segments.append(TTSSegment(text=chinese_tail, voice=CHINESE_VOICE))
    return tuple(segments) or (TTSSegment(text=normalize_spoken_text(text), voice=default_voice),)


class TTSProvider:
    model_name = "placeholder"
    model_version = "0"

    def generate(self, request: TTSRequest) -> TTSResult:
        raise NotImplementedError


class PlaceholderTTSProvider(TTSProvider):
    """Placeholder for the first API shape; real providers come next."""

    def generate(self, request: TTSRequest) -> TTSResult:
        raise RuntimeError("No TTS provider is configured yet")


class WindowsSapiTTSProvider(TTSProvider):
    model_name = "windows-sapi"
    model_version = "1"

    def generate(self, request: TTSRequest) -> TTSResult:
        settings.audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = settings.audio_dir / f"{uuid4()}.wav"
        rate = max(-10, min(10, round((request.speed - 100) / 10)))

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            suffix=".txt",
            delete=False,
        ) as text_file:
            text_file.write(request.text)
            text_path = Path(text_file.name)

        script = "\n".join(
            [
                "Add-Type -AssemblyName System.Speech",
                "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer",
                f"$synth.Rate = {rate}",
                (
                    f"$text = [System.IO.File]::ReadAllText("
                    f"'{text_path}', [System.Text.Encoding]::UTF8)"
                ),
                f"$synth.SetOutputToWaveFile('{audio_path}')",
                "$synth.Speak($text)",
                "$synth.SetOutputToNull()",
                "$synth.Dispose()",
            ]
        )

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            suffix=".ps1",
            delete=False,
        ) as script_file:
            script_file.write(script)
            script_path = Path(script_file.name)

        try:
            subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                check=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
        finally:
            text_path.unlink(missing_ok=True)
            script_path.unlink(missing_ok=True)

        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("TTS provider created an empty audio file")

        return TTSResult(audio_path=str(audio_path))


class EdgeTTSProvider(TTSProvider):
    model_name = "edge-tts"
    model_version = "15"

    CLOSING_PUNCTUATION = "\"'\u201d\u2019\uff09)]\u300b\u3011\u300d\u300f"
    DIALOGUE_OPENERS = ("\"", "'", "\u201c", "\u2018", "\u300c", "\u300e")
    DIALOGUE_MARKERS = ("\uff1a\u201c", ":\u201c", ':"', "\uff1a\u300c", ":\u300c")
    SOFT_SPEECH_MARKERS = (
        "\u4f4e\u58f0",
        "\u8f7b\u58f0",
        "\u5c0f\u58f0",
        "\u5583\u5583",
        "\u53f9\u9053",
    )
    STRONG_SPEECH_MARKERS = (
        "\u558a\u9053",
        "\u53eb\u9053",
        "\u5927\u58f0",
        "\u6012\u9053",
        "\u559d\u9053",
    )
    ENGLISH_SOFT_SPEECH_MARKERS = (
        "whispered",
        "murmured",
        "said softly",
        "asked softly",
    )
    ENGLISH_STRONG_SPEECH_MARKERS = (
        "shouted",
        "yelled",
        "screamed",
        "cried out",
    )
    QUESTION_ENDINGS = ("?", "\uff1f")
    QUESTION_PARTICLES = (
        "\u5417",
        "\u4e48",
        "\u5462",
        "\u561b",
        "\u662f\u4e0d\u662f",
        "\u6709\u6ca1\u6709",
        "\u5bf9\u4e0d\u5bf9",
        "\u597d\u4e0d\u597d",
        "\u884c\u4e0d\u884c",
    )

    def is_question(self, text: str) -> bool:
        stripped = text.strip().rstrip(self.CLOSING_PUNCTUATION)
        if stripped.endswith(self.QUESTION_ENDINGS):
            return True

        stripped_without_terminal = stripped.rstrip("\u3002.!\uff01\u2026")
        return stripped_without_terminal.endswith(self.QUESTION_PARTICLES)

    def is_dialogue(self, text: str) -> bool:
        stripped = text.strip()
        return stripped.startswith(self.DIALOGUE_OPENERS) or any(
            marker in stripped for marker in self.DIALOGUE_MARKERS
        )

    def infer_prosody(self, text: str, speed: int) -> tuple[str, str]:
        rate_delta = max(-50, min(100, speed - 100))
        pitch = "+0Hz"
        stripped = text.strip().rstrip(self.CLOSING_PUNCTUATION)
        normalized = stripped.casefold()
        sentence_length = len(stripped)

        if sentence_length >= 70:
            rate_delta -= 8
        elif sentence_length >= 42:
            rate_delta -= 4

        soft_pause_count = sum(stripped.count(mark) for mark in ("，", ",", "；", ";", "、"))
        if soft_pause_count >= 3:
            rate_delta -= 3

        if self.is_dialogue(text):
            rate_delta += 2
            pitch = "+4Hz"

        has_soft_marker = any(marker in stripped for marker in self.SOFT_SPEECH_MARKERS) or any(
            marker in normalized for marker in self.ENGLISH_SOFT_SPEECH_MARKERS
        )
        has_strong_marker = any(
            marker in stripped for marker in self.STRONG_SPEECH_MARKERS
        ) or any(marker in normalized for marker in self.ENGLISH_STRONG_SPEECH_MARKERS)
        if has_soft_marker:
            rate_delta -= 5
            pitch = "-4Hz"
        elif has_strong_marker:
            rate_delta += 5
            pitch = "+10Hz"

        if stripped.endswith(("!", "\uff01")):
            rate_delta += 4
            pitch = "+12Hz" if pitch == "+10Hz" else "+8Hz"
        elif stripped.endswith(("...", "\u2026", "\u2014\u2014")):
            rate_delta -= 8
            pitch = "-6Hz"

        rate_delta = max(-50, min(100, rate_delta))
        return f"{rate_delta:+d}%", pitch

    def generate(self, request: TTSRequest) -> TTSResult:
        import edge_tts

        settings.audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = settings.audio_dir / f"{uuid4()}.mp3"
        rate, pitch = self.infer_prosody(request.text, request.speed)
        segments = build_tts_segments(request.text, request.voice)

        async def save_audio() -> None:
            if len(segments) == 1:
                segment = segments[0]
                communicate = edge_tts.Communicate(
                    segment.text,
                    segment.voice,
                    rate=rate,
                    pitch=pitch,
                )
                await communicate.save(str(audio_path))
                return

            with audio_path.open("wb") as output:
                for segment in segments:
                    communicate = edge_tts.Communicate(
                        segment.text,
                        segment.voice,
                        rate=rate,
                        pitch=pitch,
                    )
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            output.write(chunk["data"])

        asyncio.run(save_audio())

        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("TTS provider created an empty audio file")

        return TTSResult(audio_path=str(audio_path))


def select_voice_for_text(text: str) -> str:
    cjk_count = sum(1 for char in text if "\u3400" <= char <= "\u9fff")
    latin_count = sum(1 for char in text if char.isascii() and char.isalpha())
    if latin_count and (cjk_count == 0 or latin_count >= cjk_count * 2):
        return ENGLISH_VOICE
    return CHINESE_VOICE


default_tts_provider = EdgeTTSProvider()
