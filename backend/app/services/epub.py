from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


class EPUBParseError(RuntimeError):
    pass


@dataclass(frozen=True)
class ManifestItem:
    href: str
    properties: frozenset[str]


@dataclass(frozen=True)
class SpineItem:
    idref: str
    is_linear: bool


@dataclass(frozen=True)
class ParsedDocument:
    title: str | None
    text: str
    semantic_types: frozenset[str]


@dataclass(frozen=True)
class _ElementContext:
    tag: str
    skipped: bool


class EPUBTextParser(HTMLParser):
    BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "p",
        "section",
    }
    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    SKIPPED_TAGS = {"audio", "canvas", "head", "noscript", "script", "style", "svg", "video"}
    SKIPPED_SEMANTICS = {
        "annotation",
        "endnote",
        "footnote",
        "note",
        "noteref",
        "rearnote",
    }
    SKIPPED_ROLES = {"doc-endnote", "doc-footnote", "doc-noteref"}
    SKIPPED_CLASS_OR_ID_TOKENS = {"endnote", "footnote", "footnotes", "noteref"}
    VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._contexts: list[_ElementContext] = []
        self._parts: list[str] = []
        self._document_title_parts: list[str] = []
        self._heading_parts: list[str] = []
        self._capturing_first_heading = False
        self._first_heading: str | None = None
        self._semantic_types: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {name.lower(): value or "" for name, value in attrs}
        semantic_types = _attribute_tokens(attributes, "epub:type", "type")
        self._semantic_types.update(semantic_types)

        parent_skipped = self._contexts[-1].skipped if self._contexts else False
        skipped = parent_skipped or self._should_skip(tag, attributes, semantic_types)
        if tag not in self.VOID_TAGS:
            self._contexts.append(_ElementContext(tag=tag, skipped=skipped))

        if skipped:
            return
        if tag in self.BLOCK_TAGS:
            self._parts.append("\n")
        if tag in self.HEADING_TAGS and self._first_heading is None:
            self._capturing_first_heading = True

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        matching_index = next(
            (
                index
                for index in range(len(self._contexts) - 1, -1, -1)
                if self._contexts[index].tag == tag
            ),
            None,
        )
        skipped = self._contexts[-1].skipped if self._contexts else False

        if not skipped and tag in self.HEADING_TAGS and self._capturing_first_heading:
            heading = _clean_inline_text("".join(self._heading_parts))
            self._first_heading = heading or None
            self._heading_parts.clear()
            self._capturing_first_heading = False
        if not skipped and tag in self.BLOCK_TAGS:
            self._parts.append("\n")
        if matching_index is not None:
            del self._contexts[matching_index:]

    def handle_data(self, data: str) -> None:
        context_tags = {context.tag for context in self._contexts}
        if "head" in context_tags and "title" in context_tags:
            self._document_title_parts.append(data)
        if self._contexts and self._contexts[-1].skipped:
            return

        text = _clean_inline_text(data)
        if not text:
            return
        if (
            data[:1].isspace()
            and self._parts
            and not self._parts[-1].endswith((" ", "\n"))
        ):
            self._parts.append(" ")
        self._parts.append(text)
        if data[-1:].isspace():
            self._parts.append(" ")
        if self._capturing_first_heading:
            self._heading_parts.append(data)

    def document(self) -> ParsedDocument:
        lines = [line.strip() for line in "".join(self._parts).splitlines()]
        text = "\n".join(line for line in lines if line)
        document_title = _clean_inline_text("".join(self._document_title_parts))
        title = self._first_heading or document_title or None
        if title:
            text = _remove_leading_title(text, title)
        return ParsedDocument(
            title=title,
            text=text,
            semantic_types=frozenset(self._semantic_types),
        )

    def _should_skip(
        self,
        tag: str,
        attributes: dict[str, str],
        semantic_types: set[str],
    ) -> bool:
        if tag in self.SKIPPED_TAGS or "hidden" in attributes:
            return True
        if semantic_types & self.SKIPPED_SEMANTICS:
            return True
        if _attribute_tokens(attributes, "role") & self.SKIPPED_ROLES:
            return True
        class_and_id = _attribute_tokens(attributes, "class", "id")
        return bool(class_and_id & self.SKIPPED_CLASS_OR_ID_TOKENS)


SKIPPED_MANIFEST_PROPERTIES = {"nav"}
SKIPPED_DOCUMENT_SEMANTICS = {
    "colophon",
    "copyright-page",
    "cover",
    "imprint",
    "titlepage",
    "toc",
}
SKIPPED_GUIDE_TYPES = {"colophon", "copyright-page", "cover", "title-page", "toc"}
ENCODING_RE = re.compile(br"encoding=[\"']\s*([A-Za-z0-9._-]+)\s*[\"']", re.IGNORECASE)
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def read_epub_chapters(path: Path) -> list[tuple[str, str]]:
    try:
        with ZipFile(path) as epub:
            opf_path = _find_opf_path(epub)
            opf_root = ElementTree.fromstring(epub.read(opf_path))
            manifest = _read_manifest(opf_root)
            spine = _read_spine(opf_root)
            opf_dir = PurePosixPath(opf_path).parent
            excluded_paths = _read_guide_exclusions(opf_root, opf_dir)
            archive_names = set(epub.namelist())

            chapters: list[tuple[str, str]] = []
            for index, spine_item in enumerate(spine, start=1):
                manifest_item = manifest.get(spine_item.idref)
                if manifest_item is None or not spine_item.is_linear:
                    continue
                if manifest_item.properties & SKIPPED_MANIFEST_PROPERTIES:
                    continue

                chapter_path = _resolve_archive_path(opf_dir, manifest_item.href)
                if chapter_path in excluded_paths or chapter_path not in archive_names:
                    continue
                entry = epub.getinfo(chapter_path)
                if entry.file_size > MAX_DOCUMENT_BYTES:
                    raise EPUBParseError(f"EPUB document is too large: {chapter_path}")

                document = _parse_document(_decode_document(epub.read(chapter_path)))
                if document.semantic_types & SKIPPED_DOCUMENT_SEMANTICS:
                    continue
                if document.text:
                    title = (document.title or f"Chapter {index}")[:80]
                    chapters.append((title, document.text))
    except EPUBParseError:
        raise
    except (BadZipFile, ElementTree.ParseError, KeyError, UnicodeError, ValueError) as exc:
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
                return _resolve_archive_path(PurePosixPath(), full_path)

    raise EPUBParseError("EPUB container does not reference an OPF package")


def _read_manifest(opf_root: ElementTree.Element) -> dict[str, ManifestItem]:
    manifest: dict[str, ManifestItem] = {}
    for element in opf_root.iter():
        if not element.tag.endswith("item"):
            continue
        item_id = element.attrib.get("id")
        href = element.attrib.get("href")
        media_type = element.attrib.get("media-type")
        if item_id and href and media_type in {"application/xhtml+xml", "text/html"}:
            manifest[item_id] = ManifestItem(
                href=href,
                properties=frozenset(element.attrib.get("properties", "").lower().split()),
            )
    return manifest


def _read_spine(opf_root: ElementTree.Element) -> list[SpineItem]:
    return [
        SpineItem(
            idref=element.attrib["idref"],
            is_linear=element.attrib.get("linear", "yes").lower() != "no",
        )
        for element in opf_root.iter()
        if element.tag.endswith("itemref") and "idref" in element.attrib
    ]


def _read_guide_exclusions(
    opf_root: ElementTree.Element,
    opf_dir: PurePosixPath,
) -> set[str]:
    exclusions: set[str] = set()
    for element in opf_root.iter():
        if not element.tag.endswith("reference"):
            continue
        reference_type = element.attrib.get("type", "").lower()
        href = element.attrib.get("href")
        if href and reference_type in SKIPPED_GUIDE_TYPES:
            exclusions.add(_resolve_archive_path(opf_dir, href))
    return exclusions


def _resolve_archive_path(base: PurePosixPath, href: str) -> str:
    decoded_path = unquote(urlsplit(href).path).replace("\\", "/")
    parts: list[str] = []
    for part in (base / decoded_path).parts:
        if part in {"", ".", "/"}:
            continue
        if part == "..":
            if not parts:
                raise EPUBParseError(f"EPUB path escapes package root: {href}")
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        raise EPUBParseError(f"EPUB contains an empty document path: {href}")
    return "/".join(parts)


def _decode_document(data: bytes) -> str:
    match = ENCODING_RE.search(data[:512])
    encodings = [match.group(1).decode("ascii")] if match else []
    encodings.extend(["utf-8-sig", "utf-16", "windows-1252"])
    for encoding in dict.fromkeys(encodings):
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    raise UnicodeError("Unable to decode EPUB document")


def _parse_document(html: str) -> ParsedDocument:
    parser = EPUBTextParser()
    parser.feed(html)
    parser.close()
    return parser.document()


def _attribute_tokens(attributes: dict[str, str], *names: str) -> set[str]:
    tokens: set[str] = set()
    for name in names:
        value = attributes.get(name, "").lower()
        tokens.update(token for token in re.split(r"\s+", value) if token)
    return tokens


def _clean_inline_text(text: str) -> str:
    return " ".join(text.split())


def _remove_leading_title(text: str, title: str) -> str:
    lines = text.splitlines()
    if lines and _clean_inline_text(lines[0]) == _clean_inline_text(title):
        return "\n".join(lines[1:]).strip()
    return text
