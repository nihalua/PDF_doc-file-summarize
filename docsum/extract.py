"""Turn an uploaded file (PDF, DOCX, DOC, TXT) into something Claude can read.

PDFs are kept as PDF when they're small enough, so Claude sees the real
layout, tables, charts and scanned pages. Everything else becomes plain text.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader, PdfWriter

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".doc", ".txt", ".md")

# Native PDF input: API limit is 32 MB / 600 pages per request, but every page
# also costs image tokens, so we keep native batches well below that.
PDF_PAGES_PER_BATCH = 100
PDF_MAX_BYTES_PER_BATCH = 30 * 1024 * 1024
# Below this many extracted characters per page, treat the PDF as scanned.
SCANNED_CHARS_PER_PAGE = 50


class ExtractionError(Exception):
    """The file couldn't be read."""


@dataclass
class LoadedDocument:
    filename: str
    # Exactly one of these is populated.
    text: str | None = None
    pdf_batches: list[bytes] = field(default_factory=list)
    page_count: int | None = None

    @property
    def is_pdf(self) -> bool:
        return bool(self.pdf_batches)


def load_document(filename: str, data: bytes) -> LoadedDocument:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _load_pdf(filename, data)
    if ext == ".docx":
        return LoadedDocument(filename, text=_docx_to_text(data))
    if ext == ".doc":
        return LoadedDocument(filename, text=_doc_to_text(data))
    if ext in (".txt", ".md"):
        return LoadedDocument(filename, text=_decode_text(data))
    raise ExtractionError(
        f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
    )


def _load_pdf(filename: str, data: bytes) -> LoadedDocument:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError("This PDF is password-protected.")
        pages = len(reader.pages)
    except ExtractionError:
        raise
    except Exception as e:  # pypdf raises a variety of errors on broken files
        raise ExtractionError(f"Could not read PDF: {e}") from e

    if pages == 0:
        raise ExtractionError("The PDF has no pages.")

    # Small PDF: send it whole, natively.
    if pages <= PDF_PAGES_PER_BATCH and len(data) <= PDF_MAX_BYTES_PER_BATCH:
        return LoadedDocument(filename, pdf_batches=[data], page_count=pages)

    # Large PDF: text is far cheaper than page images, so prefer it when the
    # PDF actually has a text layer.
    text = "\n\n".join(
        f"[Page {i + 1}]\n{(page.extract_text() or '').strip()}"
        for i, page in enumerate(reader.pages)
    )
    body_chars = sum(len((p.extract_text() or "").strip()) for p in reader.pages)
    if body_chars >= SCANNED_CHARS_PER_PAGE * pages:
        return LoadedDocument(filename, text=text, page_count=pages)

    # Scanned large PDF: split into native page batches.
    return LoadedDocument(
        filename, pdf_batches=_split_pdf(reader), page_count=pages
    )


def _split_pdf(reader: PdfReader) -> list[bytes]:
    batches: list[bytes] = []
    total = len(reader.pages)
    for start in range(0, total, PDF_PAGES_PER_BATCH):
        writer = PdfWriter()
        for i in range(start, min(start + PDF_PAGES_PER_BATCH, total)):
            writer.add_page(reader.pages[i])
        buf = io.BytesIO()
        writer.write(buf)
        batches.append(buf.getvalue())
    return batches


def _docx_to_text(data: bytes) -> str:
    try:
        doc = DocxDocument(io.BytesIO(data))
    except Exception as e:
        raise ExtractionError(f"Could not read DOCX: {e}") from e

    parts: list[str] = []
    # iter_inner_content keeps paragraphs and tables in document order.
    for block in doc.iter_inner_content():
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            style = (block.style.name if block.style is not None else "").lower()
            if style.startswith(("heading", "title", "başlık", "baslik")):
                text = f"## {text}"
            elif style.startswith("list"):
                text = f"- {text}"
            parts.append(text)
        elif isinstance(block, Table):
            rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in block.rows]
            if rows:
                parts.append("\n".join(rows))

    text = "\n\n".join(parts).strip()
    if not text:
        raise ExtractionError("The DOCX file contains no readable text.")
    return text


def _doc_to_text(data: bytes) -> str:
    """Legacy .doc: convert to .docx with LibreOffice, then read that."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise ExtractionError(
            "Reading legacy .doc files requires LibreOffice (soffice) to be installed. "
            "Alternatively, save the file as .docx or .pdf and upload that."
        )
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "input.doc"
        src.write_bytes(data)
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "docx", "--outdir", tmp, str(src)],
                check=True,
                capture_output=True,
                timeout=180,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise ExtractionError(f"LibreOffice could not convert the .doc file: {e}") from e
        out = Path(tmp) / "input.docx"
        if not out.exists():
            raise ExtractionError(
                "LibreOffice could not convert the .doc file (is the libreoffice-writer "
                "package installed?). You can also save it as .docx or .pdf and upload that."
            )
        return _docx_to_text(out.read_bytes())


def _decode_text(data: bytes) -> str:
    # Turkish files are often cp1254 (Windows) or iso-8859-9 rather than UTF-8.
    for enc in ("utf-8-sig", "cp1254", "iso-8859-9"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", errors="replace")
    if not text.strip():
        raise ExtractionError("The file is empty.")
    return text
