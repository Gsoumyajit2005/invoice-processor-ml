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
    ocr_text: str | None = None, *, max_ocr_chars: int = 8000
) -> str:
    """Build canonical v2 JSON extraction prompt shared across backend, train, and eval."""
    parts = [
        "Extract key invoice or receipt information from the image.",
        "Return ONLY valid JSON matching this exact schema:",
        SCHEMA_TEMPLATE_V2,
        "Rules:",
        '- "document_type" must be "invoice", "receipt", "credit_note", or "unknown".',
        '- "vendor" is the seller/merchant/issuer in the letterhead (never copy the buyer '
        'from "Bill To" / "Rechnung an"; put the recipient in "bill_to").',
        '- "receipt_number" is the primary document identifier: Invoice Number (e.g. "INV-2024-001", '
        '"Invoice No: 1234"), Tax Invoice #, Bill Number, Proforma Number (e.g. "Proforma No. 201"), '
        'Challan Number, Order Number, Rechnungs-Nr, AUFNR, etc. '
        'Always extract the document reference into "receipt_number" even for proforma invoices or receipts. '
        'If multiple numbers exist (e.g. Proforma No. and Challan No.), prefer the Invoice / Proforma number. '
        'NEVER use customer ID/account number, bank IBAN, or government tax registration IDs '
        '(GSTIN, VAT ID, Steuernummer) as receipt_number.',
        "- Use null for missing scalar fields and [] if no line items exist.",
        "- Normalize dates and due_date to YYYY-MM-DD when unambiguous.",
        "- Output plain JSON numbers without currency symbols for amounts and quantities.",
        "- For tax-inclusive receipts (e.g. 'Incl. GST', 'MwSt inkl.'), set 'total_amount' "
        "to the printed grand total; never add tax on top of a tax-inclusive total or use "
        "cash tendered/change.",
        "- Convert localized European decimals carefully: e.g. '16,0000' -> 16.0, '64,00' -> 64.0, "
        "'1.285,20' -> 1285.2, '1,234.56' -> 1234.56. Never add trailing zeros or turn decimal fractions into whole thousands "
        "(e.g. '16,0000' is 16.0, NOT 160000). Only remove dots for whole-unit Asian currencies without decimal cents (e.g. 'Rp 60.000' -> 60000).",
        "- Put a 3-letter ISO 4217 code in currency when identifiable "
        "(USD, EUR, MYR, IDR, GBP, INR).",
        "- Do not invent values not present in the document.",
    ]
    if ocr_text and ocr_text.strip():
        clipped = ocr_text.strip()
        if len(clipped) > max_ocr_chars:
            half = max_ocr_chars // 2
            clipped = f"{clipped[:half]}\n...\n{clipped[-half:]}"
        parts.append("\nOCR transcript (for exact character verification):\n" + clipped)
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
