import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from app.services.epub import read_epub_chapters

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_SAMPLE = PROJECT_ROOT / "samples" / "epub_golden" / "semantic-book"


def test_epub_golden_sample_filters_non_content_and_preserves_paragraphs(tmp_path: Path) -> None:
    epub_path = tmp_path / "semantic-book.epub"
    _pack_epub(GOLDEN_SAMPLE, epub_path)
    expected = json.loads((GOLDEN_SAMPLE / "expected.json").read_text(encoding="utf-8"))

    chapters = read_epub_chapters(epub_path)

    assert chapters == [(chapter["title"], chapter["text"]) for chapter in expected]
    combined_text = "\n".join(text for _, text in chapters)
    assert "目录" not in combined_text
    assert "Copyright" not in combined_text
    assert "脚注" not in combined_text
    assert "note must not" not in combined_text
    assert "不应作为章节" not in combined_text


def _pack_epub(source_dir: Path, target_path: Path) -> None:
    with ZipFile(target_path, "w") as epub:
        epub.writestr("mimetype", b"application/epub+zip", compress_type=ZIP_STORED)
        for source_path in sorted(source_dir.rglob("*")):
            if not source_path.is_file() or source_path.name in {"mimetype", "expected.json"}:
                continue
            archive_path = source_path.relative_to(source_dir).as_posix()
            epub.write(source_path, archive_path, compress_type=ZIP_DEFLATED)
