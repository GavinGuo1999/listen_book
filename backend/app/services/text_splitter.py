import hashlib
import re

SENTENCE_ENDINGS = {"。", "！", "？", "!", "?", "."}
ELLIPSIS_MARKS = {"…"}
TERMINAL_PUNCTUATION = SENTENCE_ENDINGS | ELLIPSIS_MARKS
CLOSING_PUNCTUATION = {"\"", "'", "”", "’", "」", "』", "》", "】", "）", ")"}
OPENING_QUOTATION = {"\"", "'", "“", "‘", "「", "『"}
ALWAYS_NON_TERMINAL_ABBREVIATIONS = {
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
    "u.s",
    "u.k",
}
CONTEXTUAL_DOT_ABBREVIATIONS = {"a.m", "p.m"}
WORD_BEFORE_DOT_RE = re.compile(r"([A-Za-z](?:[A-Za-z]|\.)*)\.$")
INITIALISM_RE = re.compile(r"(?:[A-Za-z]\.)+[A-Za-z]$")
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
        if char not in TERMINAL_PUNCTUATION:
            index += 1
            continue

        if char == "." and paragraph[index : index + 3] != "...":
            if _is_non_terminal_dot(paragraph, index):
                index += 1
                continue

        end = _consume_terminal_cluster(paragraph, index)
        cluster_end = end
        while end < len(paragraph) and paragraph[end] in CLOSING_PUNCTUATION:
            end += 1

        if _is_internal_ellipsis(paragraph, index, cluster_end, end):
            index = end
            continue
        if _is_inline_quote_continuation(paragraph, start, index, cluster_end, end):
            index = end
            continue

        sentence = _clean_sentence(paragraph[start:end])
        if sentence:
            sentences.append(sentence)
        start = end
        index = end

    tail = _clean_sentence(paragraph[start:])
    if tail:
        sentences.append(tail)
    return sentences


def _consume_terminal_cluster(text: str, index: int) -> int:
    end = index + 1
    if text[index] == "." and text[index : index + 3] == "...":
        end = index + 3
        while end < len(text) and text[end] == ".":
            end += 1

    while end < len(text) and text[end] in TERMINAL_PUNCTUATION:
        end += 1
    return end


def _is_internal_ellipsis(
    text: str,
    start: int,
    cluster_end: int,
    closing_end: int,
) -> bool:
    cluster = text[start:cluster_end]
    if not cluster or any(mark not in {".", "…"} for mark in cluster):
        return False
    if cluster == ".":
        return False
    if closing_end > cluster_end or closing_end >= len(text):
        return False

    next_index = closing_end
    while next_index < len(text) and text[next_index].isspace():
        next_index += 1
    if next_index >= len(text):
        return False

    has_spacing = next_index > closing_end
    next_char = text[next_index]
    if has_spacing and (next_char.isupper() or _is_cjk(next_char)):
        return False
    return True


def _is_inline_quote_continuation(
    text: str,
    sentence_start: int,
    punctuation_index: int,
    cluster_end: int,
    closing_end: int,
) -> bool:
    if text[punctuation_index] != "." or closing_end == cluster_end:
        return False

    opener_index = max(
        text.rfind(mark, sentence_start, punctuation_index) for mark in OPENING_QUOTATION
    )
    if opener_index <= sentence_start or not text[sentence_start:opener_index].strip():
        return False

    next_char = _next_non_space(text, closing_end)
    return bool(next_char and (next_char.islower() or _is_cjk(next_char)))


def _is_non_terminal_dot(text: str, index: int) -> bool:
    if text[index] != ".":
        return False

    previous_char = text[index - 1] if index > 0 else ""
    next_char = text[index + 1] if index + 1 < len(text) else ""
    if previous_char.isalnum() and next_char.isalnum():
        return True

    prefix = text[: index + 1]
    match = WORD_BEFORE_DOT_RE.search(prefix)
    if not match:
        return False

    word = match.group(1).lower()
    if word in ALWAYS_NON_TERMINAL_ABBREVIATIONS:
        return True

    next_significant = _next_non_space(text, index + 1)
    if word in CONTEXTUAL_DOT_ABBREVIATIONS:
        return bool(next_significant and next_significant.islower())
    if INITIALISM_RE.fullmatch(match.group(1)):
        return True

    if len(word) == 1 and next_significant.isalpha():
        return True

    return False


def _next_non_space(text: str, start: int) -> str:
    for char in text[start:]:
        if not char.isspace():
            return char
    return ""


def _is_cjk(char: str) -> bool:
    return "\u3400" <= char <= "\u9fff"


def _clean_sentence(text: str) -> str:
    stripped = text.strip()
    if PRESERVE_SPACING_RE.match(stripped):
        return SENTENCE_SPACING_RE.sub(" ", stripped)
    return stripped


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
