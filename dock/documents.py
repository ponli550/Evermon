"""Read an attachment in whatever format it arrived in, and render it to one canonical form.

The canonical form is deliberately boring text::

    BILL OF LADING (DRAFT)
    Shipper: APRIL FAR EAST (M) SDN BHD
      TOWER 2, AVENUE 5; 59200 KUALA LUMPUR
    Load Port: NHAVA SHEVA, INDIA

One "Label: value" line per field, continuation lines indented. Everything downstream
sees only that, so adding a format means adding a renderer here and nothing else.

Only the standard library is used. OOXML files are zipped XML; the text layer of these
PDFs is ASCII85 + Flate, both of which ship with Python. A scanned page has no text
layer at all, and rather than guess at one this module raises Unreadable so the
pipeline can escalate to a person.
"""

from __future__ import annotations

import base64
import re
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree

__all__ = ["Unreadable", "render"]


class Unreadable(Exception):
    """The attachment exists but no text could be recovered from it."""


# --- OOXML ------------------------------------------------------------------

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _as_line(cells: list[str]) -> str:
    """Render one table row. Two columns are a label and its value."""
    cells = [c.strip() for c in cells]
    while cells and not cells[-1]:
        cells.pop()
    if len(cells) >= 2 and cells[0]:
        head, *rest = cells
        value, *extra = [c for c in rest if c]
        lines = [f"{head}: {value}"] + [f"  {c}" for c in extra]
        return "\n".join(lines)
    return cells[0] if cells else ""


def _render_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise Unreadable(f"{path.name}: not a readable Word document") from exc

    def paragraphs(node: ElementTree.Element) -> list[str]:
        """One entry per visual line: Word breaks an address with <w:br/>, not <w:p>."""
        out = []
        for para in node.iter(f"{_W}p"):
            pieces: list[str] = []
            for elem in para.iter():
                if elem.tag == f"{_W}t":
                    pieces.append(elem.text or "")
                elif elem.tag == f"{_W}br":
                    pieces.append("\n")
            out.extend(line.strip() for line in "".join(pieces).split("\n") if line.strip())
        return out

    lines: list[str] = []
    body = root.find(f"{_W}body")
    for child in body if body is not None else []:
        if child.tag == f"{_W}p":
            lines.extend(paragraphs(child))
        elif child.tag == f"{_W}tbl":
            for row in child.iter(f"{_W}tr"):
                cells = [paragraphs(tc) for tc in row.iter(f"{_W}tc")]
                if len(cells) >= 2 and cells[0] and cells[1]:
                    # The address lines below the party name are continuations, exactly
                    # as they are in the plain-text documents.
                    lines.append(f"{cells[0][0]}: {cells[1][0]}")
                    lines.extend(f"  {extra}" for extra in cells[1][1:])
                elif cells and cells[0]:
                    lines.append(cells[0][0])
    return "\n".join(lines)


def _column(ref: str) -> str:
    return "".join(ch for ch in ref if ch.isalpha())


def _render_xlsx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            shared = _shared_strings(archive)
            sheets = [n for n in archive.namelist() if n.startswith("xl/worksheets/sheet")]
            if not sheets:
                raise Unreadable(f"{path.name}: workbook has no sheets")
            root = ElementTree.fromstring(archive.read(sorted(sheets)[0]))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise Unreadable(f"{path.name}: not a readable workbook") from exc

    lines: list[str] = []
    for row in root.iter(f"{_S}row"):
        cells: list[str] = []
        for cell in row.iter(f"{_S}c"):
            text = "".join(t.text or "" for t in cell.iter(f"{_S}t"))
            if cell.get("t") == "s" and text == "":
                value = cell.find(f"{_S}v")
                if value is not None and value.text is not None:
                    text = shared[int(value.text)]
            if not text:
                value = cell.find(f"{_S}v")
                text = (value.text or "") if value is not None else ""
            cells.append(text)
        # Preserve column position so a value in B with an empty A stays a continuation.
        line = _as_line(cells)
        if line:
            lines.append(line)
        elif cells and _column(next(iter(row.iter(f"{_S}c"))).get("r") or "A") != "A":
            lines.append(f"  {cells[0]}")
    return "\n".join(lines)


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(f"{_S}t")) for si in root.iter(f"{_S}si")]


# --- PDF --------------------------------------------------------------------

# A stream dictionary, then its bytes. The dictionary body is kept free of nested
# dictionaries so a page's /ProcSet cannot be mistaken for the stream's own filters.
_PDF_STREAM = re.compile(
    rb"<<(?P<head>(?:[^<>]|<<[^<>]*>>)*)>>\s*stream\r?\n(?P<body>.*?)\s*endstream", re.DOTALL
)
# ReportLab positions every run absolutely, which hands us the column for free.
_PDF_SHOW = re.compile(
    rb"1 0 0 1 (?P<x>[\d.]+) (?P<y>[\d.]+) Tm\s+\((?P<text>(?:[^()\\]|\\.)*)\)\s*Tj"
)
_PDF_ESCAPE = re.compile(rb"\\([()\\])")

#: Left edge of the label column; anything further right is a value or a table cell.
_LABEL_X = 100.0


def _pdf_content(raw: bytes) -> bytes:
    chunks: list[bytes] = []
    for match in _PDF_STREAM.finditer(raw):
        head, body = match.group("head"), match.group("body")
        if b"/Image" in head:
            continue
        try:
            if b"ASCII85Decode" in head:
                body = base64.a85decode(body.strip(), adobe=True)
            if b"FlateDecode" in head:
                body = zlib.decompress(body)
        except (ValueError, zlib.error):
            continue
        if b" Tj" in body:
            chunks.append(body)
    return b"\n".join(chunks)


def _render_pdf(path: Path) -> str:
    raw = path.read_bytes()
    if not raw.startswith(b"%PDF"):
        raise Unreadable(f"{path.name}: not a PDF")
    content = _pdf_content(raw)
    runs = [
        (round(float(m.group("y")), 1), float(m.group("x")), _pdf_text(m.group("text")))
        for m in _PDF_SHOW.finditer(content)
    ]
    if not runs:
        raise Unreadable(f"{path.name}: no text layer (scanned image or damaged file)")

    lines: list[str] = []
    for y in sorted({r[0] for r in runs}, reverse=True):
        row = sorted((r for r in runs if r[0] == y), key=lambda r: r[1])
        if len(row) > 2:
            # A manifest row (container no. / description / weight), not a field.
            continue
        if len(row) == 2:
            lines.append(f"{row[0][2]}: {row[1][2]}")
        elif row[0][1] > _LABEL_X:
            lines.append(f"  {row[0][2]}")
        else:
            lines.append(row[0][2])
    return "\n".join(lines)


def _pdf_text(raw: bytes) -> str:
    return _PDF_ESCAPE.sub(rb"\1", raw).decode("latin-1").strip()


# --- entry point ------------------------------------------------------------

_RENDERERS = {".docx": _render_docx, ".xlsx": _render_xlsx, ".pdf": _render_pdf}


def render(path: str | Path) -> str:
    """Return the canonical text of an attachment, or raise Unreadable."""
    path = Path(path)
    if not path.is_file():
        raise Unreadable(f"{path.name}: attachment not found")
    suffix = path.suffix.lower()
    if suffix in (".txt", ".text"):
        text = path.read_bytes().decode("utf-8", errors="replace")
    elif suffix in _RENDERERS:
        text = _RENDERERS[suffix](path)
    else:
        raise Unreadable(f"{path.name}: unsupported attachment type '{suffix}'")
    if not text.strip():
        raise Unreadable(f"{path.name}: rendered to no text")
    return text
