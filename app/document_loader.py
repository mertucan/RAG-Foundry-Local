from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re

from .chunker import parse_front_matter
from .config import config


SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}


@dataclass(frozen=True)
class LoadedDocument:
    doc_id: str
    title: str
    category: str
    body: str
    filename: str = ""
    tags: str = ""
    course: str = ""
    topic: str = ""
    semester: str = ""
    source_type: str = ""


def is_supported_document(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def load_document_from_path(file_path: Path) -> LoadedDocument:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf_document(file_path.read_bytes(), file_path.name)
    if suffix in {".md", ".txt"}:
        return load_text_document(file_path.read_text(encoding="utf-8"), file_path.name)
    raise ValueError(f"Unsupported document type: {suffix}")


def load_document_from_upload(filename: str, content: bytes) -> LoadedDocument:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return load_pdf_document(content, filename)
    if suffix in {".md", ".txt"}:
        return load_text_document(content.decode("utf-8"), filename)
    raise ValueError(f"Unsupported document type: {suffix}")


def load_text_document(raw: str, filename: str) -> LoadedDocument:
    meta, body = parse_front_matter(raw)
    stem = Path(filename).stem
    return LoadedDocument(
        doc_id=meta.get("id") or stem,
        title=meta.get("title") or filename,
        category=meta.get("category") or "Uploaded Notes",
        body=body,
        filename=filename,
        tags=meta.get("tags", ""),
        course=meta.get("course", ""),
        topic=meta.get("topic", ""),
        semester=meta.get("semester", ""),
        source_type=meta.get("source_type") or Path(filename).suffix.lower().lstrip("."),
    )


def load_pdf_document(content: bytes, filename: str) -> LoadedDocument:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - only hit when dependency is missing
        raise RuntimeError("PDF support requires pypdf. Run: pip install -r requirements.txt") from exc

    reader = PdfReader(BytesIO(content))
    pages: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(f"# Page {page_number}\n\n{text}")

    body = "\n\n".join(pages).strip()
    if not body:
        body = ocr_pdf_document(content)
    if not body:
        raise ValueError("No extractable text found in PDF. Scanned image-only PDFs may need OCR.")

    metadata = reader.metadata or {}
    raw_title = getattr(metadata, "title", None)
    if not raw_title and hasattr(metadata, "get"):
        raw_title = metadata.get("/Title")
    title = str(raw_title).strip() if raw_title else Path(filename).stem
    return LoadedDocument(
        doc_id=Path(filename).stem,
        title=title or Path(filename).stem,
        category="PDF Notes",
        body=body,
        filename=filename,
        source_type="pdf",
    )


def page_number_for_chunk(chunk: str) -> int | None:
    matches = list(re.finditer(r"# Page (\d+)(?: OCR)?", chunk))
    if not matches:
        return None
    return int(matches[-1].group(1))


def ocr_pdf_document(content: bytes) -> str:
    if not config.ocr_enabled:
        raise ValueError("No extractable text found in PDF. OCR is disabled.")

    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - only hit when optional OCR deps are missing
        raise RuntimeError("OCR support requires pymupdf, pytesseract, and pillow. Run: pip install -r requirements.txt") from exc

    if config.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = config.tesseract_cmd

    try:
        pdf = fitz.open(stream=content, filetype="pdf")
        matrix = fitz.Matrix(config.ocr_dpi / 72, config.ocr_dpi / 72)
        pages: list[str] = []
        for page_number, page in enumerate(pdf, start=1):
            if page_number > config.ocr_max_pages:
                break
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes("png")))
            text = pytesseract.image_to_string(image, lang=config.ocr_language).strip()
            if text:
                pages.append(f"# Page {page_number} OCR\n\n{text}")
        return "\n\n".join(pages).strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "OCR needs the Tesseract app installed. On Windows run: winget install UB-Mannheim.TesseractOCR"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"OCR failed: {exc}") from exc
