"""Pluggable extraction protocols, prompts, and result dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.core.reconciliation import ReconciliationResult
from app.core.schemas import InvoiceExtraction
from app.pdf.processor import ProcessedDocument

SCHEMA_TEMPLATE_V2 = """{
  "document_type": "invoice",
  "vendor": null,
  "vendor_address": null,
  "receipt_number": null,
  "date": null,
  "due_date": null,
  "currency": null,
  "subtotal": null,
  "tax_amount": null,
  "discount_amount": null,
  "total_amount": null,
  "bill_to": null,
  "line_items": [
    {
      "description": "",
      "quantity": null,
      "unit_price": null,
      "total_price": null
    }
  ]
}"""


def build_v2_extraction_prompt(
    ocr_text: str | None = None, *, max_ocr_chars: int = 10000
) -> str:
    """Build v2 JSON extraction prompt with optional Indra OCR transcript grounding."""
    parts = [
        "Extract structured invoice or receipt fields from the document.",
        "Return ONLY valid JSON matching this exact schema:",
        SCHEMA_TEMPLATE_V2,
        "Rules:",
        '- "document_type" must be one of "invoice", "receipt", "credit_note", or "unknown".',
        "- Use null for missing scalar fields and [] if no line items exist.",
        "- Normalize dates and due_date to YYYY-MM-DD when unambiguous.",
        "- Output plain JSON numbers without currency symbols for amounts and quantities.",
        "- Convert localized numbers carefully (e.g. '1.285,20' -> 1285.2, "
        "'1,234.56' -> 1234.56; whole-unit '60.000' -> 60000).",
        "- Put a 3-letter ISO 4217 code in currency when identifiable "
        "(USD, EUR, MYR, IDR, GBP, INR).",
        "- Do not invent values not present in the document.",
    ]
    if ocr_text and ocr_text.strip():
        clipped = ocr_text.strip()
        if len(clipped) > max_ocr_chars:
            half = max_ocr_chars // 2
            clipped = f"{clipped[:half]}\n...\n{clipped[-half:]}"
        parts.append("\nOCR transcript (for exact value verification):\n" + clipped)
    return "\n".join(parts)


@dataclass(frozen=True)
class OcrLine:
    """Single OCR text line with page-normalized [0..1000] coordinates."""

    page: int
    text: str
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


@dataclass
class OcrDocumentResult:
    """Aggregated OCR output across all pages of a processed document."""

    markdown: str
    plain_text: str
    lines: list[OcrLine] = field(default_factory=list)
    latency_ms: int = 0


@dataclass(frozen=True)
class CloudConfig:
    """Ephemeral per-request BYO-key configuration (never persisted or logged)."""

    provider: str | None = None
    model: str | None = None
    api_key: str | None = None


@dataclass
class ExtractionRunResult:
    """End-to-end result produced by the extraction router."""

    extraction: InvoiceExtraction
    extractor_used: str
    ocr: OcrDocumentResult
    reconciliation: ReconciliationResult
    latency_ms: int
    raw_model_output: str = ""


class ExtractorBackend(Protocol):
    """Protocol implemented by local and cloud VLM extractors."""

    name: str

    async def extract(
        self,
        doc: ProcessedDocument,
        ocr: OcrDocumentResult,
        *,
        cloud_config: CloudConfig | None = None,
    ) -> tuple[InvoiceExtraction, str]:
        """Run extraction over document pages and OCR transcript."""
        ...
