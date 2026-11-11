"""Multi-page PDF rasterization (pypdfium2 + pdfplumber) and image normalization."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


class DocumentValidationError(ValueError):
    """Raised when uploaded file bytes are empty, corrupted, or exceed page bounds."""


class UnsupportedMediaTypeError(DocumentValidationError):
    """Raised when magic-byte signature does not match PDF/JPEG/PNG/WEBP."""


@dataclass
class ProcessedPage:
    """Rendered single document page ready for OCR, VLMs, and page viewer storage."""

    page_number: int
    image: Image.Image
    width: int
    height: int
    native_text: str
    png_bytes: bytes


@dataclass
class ProcessedDocument:
    """Normalized document container across images and multi-page PDFs."""

    filename: str
    mime_type: str
    page_count: int
    is_pdf: bool
    has_native_text: bool
    pages: list[ProcessedPage]


def detect_mime_type(content: bytes) -> str:
    """Detect supported document MIME type using strict magic-byte inspection."""
    if not content:
        raise DocumentValidationError("Uploaded file is empty.")
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    raise UnsupportedMediaTypeError(
        "Unsupported file format. Only PDF, JPEG, PNG, and WEBP documents are allowed."
    )


def _encode_png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _extract_pdf_native_texts(content: bytes, expected_pages: int) -> list[str]:
    texts = [""] * expected_pages
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for idx, page in enumerate(pdf.pages[:expected_pages]):
                texts[idx] = (page.extract_text() or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.debug("pdfplumber native text extraction failed; relying on visual OCR: %s", exc)
    return texts


def process_document(
    content: bytes,
    *,
    filename: str,
    max_pages: int = 20,
    dpi: float = 150.0,
) -> ProcessedDocument:
    """Validate uploaded bytes and produce normalized RGB page images + native PDF text."""
    mime_type = detect_mime_type(content)

    if mime_type == "application/pdf":
        scale = dpi / 72.0
        try:
            pdf = pdfium.PdfDocument(content)
        except Exception as exc:
            raise DocumentValidationError(f"Failed to parse PDF document: {exc}") from exc

        try:
            total_pages = len(pdf)
            if total_pages == 0:
                raise DocumentValidationError("Uploaded PDF contains 0 pages.")
            if total_pages > max_pages:
                raise DocumentValidationError(
                    f"PDF has {total_pages} pages, exceeding the configured limit of {max_pages}."
                )

            native_texts = _extract_pdf_native_texts(content, total_pages)
            pages: list[ProcessedPage] = []
            for idx in range(total_pages):
                pdf_page = pdf[idx]
                try:
                    bitmap = pdf_page.render(scale=scale)  # type: ignore[arg-type]
                    pil_image = bitmap.to_pil().convert("RGB")
                finally:
                    pdf_page.close()
                pages.append(
                    ProcessedPage(
                        page_number=idx + 1,
                        image=pil_image,
                        width=pil_image.width,
                        height=pil_image.height,
                        native_text=native_texts[idx],
                        png_bytes=_encode_png(pil_image),
                    )
                )
        finally:
            pdf.close()

        has_native = any(bool(p.native_text) for p in pages)
        return ProcessedDocument(
            filename=filename,
            mime_type=mime_type,
            page_count=len(pages),
            is_pdf=True,
            has_native_text=has_native,
            pages=pages,
        )

    # Single-page raster image (JPEG / PNG / WEBP)
    try:
        with Image.open(io.BytesIO(content)) as raw_img:
            transposed = ImageOps.exif_transpose(raw_img)
            pil_image = transposed.convert("RGB")
    except Exception as exc:
        raise DocumentValidationError(f"Corrupted or unreadable image file: {exc}") from exc

    page = ProcessedPage(
        page_number=1,
        image=pil_image,
        width=pil_image.width,
        height=pil_image.height,
        native_text="",
        png_bytes=_encode_png(pil_image),
    )
    return ProcessedDocument(
        filename=filename,
        mime_type=mime_type,
        page_count=1,
        is_pdf=False,
        has_native_text=False,
        pages=[page],
    )
