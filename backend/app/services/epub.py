from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


class EPUBParseError(RuntimeError):
    pass


class EPUBTextParser(HTMLParser):
    BLOCK_TAGS = {
        "blockquote",
        "br",
        "dd",
        "div",
        "dt",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "p",
    }
    SKIPPED_TAGS = {"head", "script", "style", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIPPED_TAGS:
            self._skip_depth += 1
        if tag in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIPPED_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = " ".join(data.split())
        if text:
            self._parts.append(text)

    def text(self) -> str:
        lines = [line.strip() for line in "".join(self._parts).splitlines()]
        return "\n".join(line for line in lines if line)


def read_epub_chapters(path: Path) -> list[tuple[str, str]]:
    try:
        with ZipFile(path) as epub:
            opf_path = _find_opf_path(epub)
            opf_xml = epub.read(opf_path)
            opf_root = ElementTree.fromstring(opf_xml)
            manifest = _read_manifest(opf_root)
            spine = _read_spine(opf_root)
            opf_dir = PurePosixPath(opf_path).parent

            chapters: list[tuple[str, str]] = []
            for index, idref in enumerate(spine, start=1):
                href = manifest.get(idref)
                if href is None:
                    continue

                chapter_path = str((opf_dir / href).as_posix())
                if chapter_path not in epub.namelist():
                    continue

                html = epub.read(chapter_path).decode("utf-8", errors="replace")
                text = _html_to_text(html)
                if text:
                    title = _chapter_title(text, index)
                    chapters.append((title, text))
    except (BadZipFile, ElementTree.ParseError, KeyError) as exc:
        raise EPUBParseError(f"Invalid EPUB file: {exc}") from exc

    if not chapters:
        raise EPUBParseError("EPUB contains no readable spine chapters")

    return chapters


def _find_opf_path(epub: ZipFile) -> str:
    try:
        container_xml = epub.read("META-INF/container.xml")
    except KeyError as exc:
        raise EPUBParseError("EPUB missing META-INF/container.xml") from exc

    root = ElementTree.fromstring(container_xml)
    for element in root.iter():
        if element.tag.endswith("rootfile"):
            full_path = element.attrib.get("full-path")
            if full_path:
                return full_path

    raise EPUBParseError("EPUB container does not reference an OPF package")


def _read_manifest(opf_root: ElementTree.Element) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for element in opf_root.iter():
        if not element.tag.endswith("item"):
            continue
        item_id = element.attrib.get("id")
        href = element.attrib.get("href")
        media_type = element.attrib.get("media-type")
        if item_id and href and media_type in {"application/xhtml+xml", "text/html"}:
            manifest[item_id] = href
    return manifest


def _read_spine(opf_root: ElementTree.Element) -> list[str]:
    return [
        element.attrib["idref"]
        for element in opf_root.iter()
        if element.tag.endswith("itemref") and "idref" in element.attrib
    ]


def _html_to_text(html: str) -> str:
    parser = EPUBTextParser()
    parser.feed(html)
    parser.close()
    return parser.text()


def _chapter_title(text: str, index: int) -> str:
    first_line = text.splitlines()[0].strip()
    return first_line[:80] if first_line else f"Chapter {index}"
