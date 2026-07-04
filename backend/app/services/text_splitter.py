import hashlib
import re

SENTENCE_ENDINGS = {"。", "！", "？", "!", "?", "."}
CLOSING_PUNCTUATION = {"\"", "'", "”", "’", "」", "』", "》", "】", "）", ")"}
DOT_ABBREVIATIONS = {
    "mr",
    "mrs",
    "ms",
    "dr",
    "prof",
    "sr",
    "jr",
    "st",
    "vs",
    "etc",
    "e.g",
    "i.e",
    "a.m",
    "p.m",
}
WORD_BEFORE_DOT_RE = re.compile(r"([A-Za-z](?:[A-Za-z]|\.)*)\.$")
SENTENCE_SPACING_RE = re.compile(r"\s+")

PRESERVE_SPACING_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9 .,'\"():;\-]*[A-Za-z0-9.!?\"')]$"
)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def split_paragraphs(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [part.strip() for part in re.split(r"\n{1,}", normalized) if part.strip()]


def split_sentences(paragraph: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    index = 0
    while index < len(paragraph):
        char = paragraph[index]
        if char not in SENTENCE_ENDINGS or _is_non_terminal_dot(paragraph, index):
            index += 1
            continue

        end = index + 1
        while end < len(paragraph) and paragraph[end] in CLOSING_PUNCTUATION:
            end += 1

        sentence = _clean_sentence(paragraph[start:end])
        if sentence:
            sentences.append(sentence)
        start = end
        index = end

    tail = _clean_sentence(paragraph[start:])
    if tail:
        sentences.append(tail)
    return sentences


def _is_non_terminal_dot(text: str, index: int) -> bool:
    if text[index] != ".":
        return False

    previous_char = text[index - 1] if index > 0 else ""
    next_char = text[index + 1] if index + 1 < len(text) else ""
    if previous_char.isdigit() and next_char.isdigit():
        return True

    prefix = text[: index + 1]
    match = WORD_BEFORE_DOT_RE.search(prefix)
    if not match:
        return False

    word = match.group(1).lower()
    if word in DOT_ABBREVIATIONS:
        return True

    if len(word) == 1 and next_char.isalpha():
        return True

    return False


def _clean_sentence(text: str) -> str:
    stripped = text.strip()
    if PRESERVE_SPACING_RE.match(stripped):
        return SENTENCE_SPACING_RE.sub(" ", stripped)
    return stripped


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
