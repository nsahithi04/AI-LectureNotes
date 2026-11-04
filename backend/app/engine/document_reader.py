"""Getting the text out of lecture documents: PDF, Word (.docx) and PowerPoint (.pptx).

Only documents with selectable text work. Scanned pages are images, so they'd need OCR, which isn't
supported yet. Word and PowerPoint files are ZIP archives of XML, so they're read with the standard
library, after checking that their XML can't expand to an unreasonable size.
"""

import logging
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core import config
from app.engine.errors import EngineError
from app.engine.schemas import SourceInfo

logger = logging.getLogger(__name__)

# Fewer characters than this per page usually means scanned images, or only page numbers.
MIN_CHARACTERS_PER_PAGE = 20
MIN_CHARACTERS = 30
# The XML of a large lecture document is a few megabytes. More than this suggests a ZIP bomb.
MAX_XML_BYTES = 50 * 1024 * 1024

EXTENSIONS = [".pdf", ".docx", ".pptx"]
FORMAT_NAMES = {".pdf": "PDF", ".docx": "Word document", ".pptx": "PowerPoint file"}

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PACKAGE_RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _clean(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _too_many_pages(pages: int, unit: str) -> EngineError:
    return EngineError("document_too_long", f"Documents can have up to {config.MAX_DOCUMENT_PAGES} {unit}.")


def _read_pdf(path: Path) -> tuple[str, int]:
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise EngineError("invalid_document", "This PDF is password protected. Remove the password and try again.")
    pages = len(reader.pages)
    if pages > config.MAX_DOCUMENT_PAGES:
        raise _too_many_pages(pages, "pages")
    text = "\n\n".join(page for page in (_clean(page.extract_text() or "") for page in reader.pages) if page)
    if pages == 0 or len(text) < MIN_CHARACTERS_PER_PAGE * pages:
        raise EngineError("no_text", "This PDF has little or no selectable text. Scanned PDFs aren't supported yet.")
    return text, pages


def _xml(archive: zipfile.ZipFile, name: str) -> ElementTree.Element:
    return ElementTree.fromstring(archive.read(name))


def _paragraph_text(paragraph: ElementTree.Element, text_tag: str) -> str:
    return "".join(node.text or "" for node in paragraph.iter(text_tag)).strip()


def _paragraphs(root: ElementTree.Element, ns: str) -> list[str]:
    """Lines of text in document order. Each table row becomes one line, with its cells separated by " | "."""
    in_tables = {id(paragraph) for table in root.iter(f"{ns}tbl") for paragraph in table.iter(f"{ns}p")}
    lines = []
    for element in root.iter():
        if element.tag == f"{ns}tr":
            cells = [" ".join(_paragraph_text(p, f"{ns}t") for p in cell.iter(f"{ns}p")).strip() for cell in element.iter(f"{ns}tc")]
            if any(cells):
                lines.append(" | ".join(cells))
        elif element.tag == f"{ns}p" and id(element) not in in_tables:
            text = _paragraph_text(element, f"{ns}t")
            if text:
                lines.append(text)
    return lines


def _read_docx(archive: zipfile.ZipFile) -> str:
    return "\n\n".join(_paragraphs(_xml(archive, "word/document.xml"), W))


def _relationships(archive: zipfile.ZipFile, part: str) -> list[ElementTree.Element]:
    folder, name = posixpath.split(part)
    rels = posixpath.join(folder, "_rels", f"{name}.rels")
    return list(_xml(archive, rels).iter(f"{PACKAGE_RELS}Relationship")) if rels in archive.namelist() else []


def _target(part: str, target: str) -> str:
    return posixpath.normpath(posixpath.join(posixpath.dirname(part), target))


def _slide_parts(archive: zipfile.ZipFile) -> list[str]:
    """Slides in presentation order, as the presentation lists them."""
    targets = {rel.get("Id"): _target("ppt/presentation.xml", rel.get("Target", "")) for rel in _relationships(archive, "ppt/presentation.xml")}
    order = [slide.get(f"{R}id") for slide in _xml(archive, "ppt/presentation.xml").iter(f"{P}sldId")]
    return [targets[rel_id] for rel_id in order if rel_id in targets and targets[rel_id] in archive.namelist()]


def _read_pptx(archive: zipfile.ZipFile) -> tuple[str, int]:
    slides = _slide_parts(archive)
    if len(slides) > config.MAX_DOCUMENT_PAGES:
        raise _too_many_pages(len(slides), "slides")

    blocks = []
    for number, part in enumerate(slides, start=1):
        lines = _paragraphs(_xml(archive, part), A)
        for rel in _relationships(archive, part):
            if rel.get("Type", "").endswith("/notesSlide"):
                notes_part = _target(part, rel.get("Target", ""))
                if notes_part in archive.namelist():
                    # Skip the slide number, which the notes page shows as a lone number.
                    notes = [line for line in _paragraphs(_xml(archive, notes_part), A) if not line.isdigit()]
                    if notes:
                        lines.append("Speaker notes: " + " ".join(notes))
        if lines:
            blocks.append(f"Slide {number}\n" + "\n".join(lines))
    return "\n\n".join(blocks), len(slides)


def _check_archive(archive: zipfile.ZipFile, required: str, kind: str) -> None:
    if required not in archive.namelist():
        raise EngineError("invalid_document", f"This file isn't a valid {kind}, or it's damaged.")
    xml_size = sum(info.file_size for info in archive.infolist() if info.filename.endswith((".xml", ".rels")))
    if xml_size > MAX_XML_BYTES:
        raise EngineError("invalid_document", f"This {kind} is too large to read.")


def read_document(path: Path, filename: str, size: int) -> tuple[SourceInfo, str]:
    """Return the document's details and its text, with paragraphs or slides separated by blank lines."""
    extension = path.suffix.lower()
    kind = FORMAT_NAMES.get(extension)
    if kind is None:
        raise EngineError("invalid_document", "Only PDF, Word (.docx) and PowerPoint (.pptx) files are supported.")

    pages = None
    try:
        if extension == ".pdf":
            text, pages = _read_pdf(path)
        else:
            with zipfile.ZipFile(path) as archive:
                if extension == ".docx":
                    _check_archive(archive, "word/document.xml", kind)
                    text = _clean(_read_docx(archive))
                else:
                    _check_archive(archive, "ppt/presentation.xml", kind)
                    text, pages = _read_pptx(archive)
                    text = _clean(text)
    except EngineError:
        raise
    except (PdfReadError, zipfile.BadZipFile, ElementTree.ParseError, ValueError, OSError, KeyError, TypeError) as exc:
        logger.warning("Could not read %s: %s", filename, exc)
        raise EngineError("invalid_document", f"This file isn't a valid {kind}, or it's damaged.") from exc

    if len(text) < MIN_CHARACTERS:
        raise EngineError("no_text", f"This {kind} has little or no text to make notes from.")
    return SourceInfo(type="document", format=extension.lstrip("."), filename=filename, size=size, pages=pages, characters=len(text)), text
