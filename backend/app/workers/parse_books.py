from pathlib import Path
from uuid import UUID

from app.db.session import SessionLocal
from app.models.book import Book, BookStatus, Chapter, Paragraph, Sentence
from app.models.job import Job
from app.services.epub import read_epub_chapters
from app.services.text_splitter import split_paragraphs, split_sentences, text_hash

TXT_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "big5")


def read_txt_text(path: Path) -> str:
    data = path.read_bytes()
    errors: list[str] = []

    for encoding in TXT_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")

    raise UnicodeDecodeError(
        "txt",
        data,
        0,
        min(1, len(data)),
        "Unable to decode TXT file. Tried: " + "; ".join(errors),
    )


def parse_txt_book(job: Job) -> None:
    book_id = UUID(job.payload["book_id"])
    storage_path = Path(job.payload["storage_path"])

    with SessionLocal() as db:
        book = db.get(Book, book_id)
        if book is None:
            raise RuntimeError(f"Book not found: {book_id}")

        book.status = BookStatus.PARSING.value
        book.error_message = None
        db.commit()

        raw_text = read_txt_text(storage_path)
        insert_chapters(db, book, [("\u6b63\u6587", raw_text)])

        book.status = BookStatus.READY.value
        db.commit()


def parse_epub_book(job: Job) -> None:
    book_id = UUID(job.payload["book_id"])
    storage_path = Path(job.payload["storage_path"])

    with SessionLocal() as db:
        book = db.get(Book, book_id)
        if book is None:
            raise RuntimeError(f"Book not found: {book_id}")

        book.status = BookStatus.PARSING.value
        book.error_message = None
        db.commit()

        insert_chapters(db, book, read_epub_chapters(storage_path))

        book.status = BookStatus.READY.value
        db.commit()


def insert_chapters(db, book: Book, chapters: list[tuple[str, str]]) -> None:
    for chapter_index, (chapter_title, chapter_text) in enumerate(chapters):
        chapter = Chapter(book_id=book.id, title=chapter_title, chapter_index=chapter_index)
        db.add(chapter)
        db.flush()

        for paragraph_index, paragraph_text in enumerate(split_paragraphs(chapter_text)):
            paragraph = Paragraph(
                chapter_id=chapter.id,
                paragraph_index=paragraph_index,
                text=paragraph_text,
            )
            db.add(paragraph)
            db.flush()

            for sentence_index, sentence_text in enumerate(split_sentences(paragraph_text)):
                db.add(
                    Sentence(
                        paragraph_id=paragraph.id,
                        sentence_index=sentence_index,
                        text=sentence_text,
                        text_hash=text_hash(sentence_text),
                    )
                )


def run_once() -> int:
    from app.workers.jobs import run_once as run_next_job

    return run_next_job()


if __name__ == "__main__":
    processed = run_once()
    print(f"processed={processed}")
