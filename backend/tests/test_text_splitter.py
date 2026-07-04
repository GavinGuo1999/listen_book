import pytest

from app.services.text_splitter import split_paragraphs, split_sentences


@pytest.mark.parametrize(
    ("paragraph", "expected"),
    [
        ("“你去哪儿？”她问。", ["“你去哪儿？”", "她问。"]),
        ("他说：“我不知道……也许明天吧。”", ["他说：“我不知道……也许明天吧。”"]),
        ("Chapter 1. Mr. Smith arrived at 3 p.m.", ["Chapter 1.", "Mr. Smith arrived at 3 p.m."]),
        ("第一章  雨夜", ["第一章  雨夜"]),
    ],
)
def test_sentence_splitter_golden_cases(paragraph: str, expected: list[str]) -> None:
    assert split_sentences(paragraph) == expected


def test_split_paragraphs_normalizes_blank_lines_and_whitespace() -> None:
    assert split_paragraphs(" 第一段。\r\n\r\n  第二段。 \n\n") == ["第一段。", "第二段。"]
