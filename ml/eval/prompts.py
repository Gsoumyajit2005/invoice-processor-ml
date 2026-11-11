"""Structured extraction prompts aligned with Xiaomi-OCR-0 and Qwen3.5 VLM formatting."""

from __future__ import annotations

SCHEMA_TEMPLATE = """{
  "vendor": null,
  "vendor_address": null,
  "receipt_number": null,
  "date": null,
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


def build_extraction_prompt(ocr_text: str | None = None, *, max_ocr_chars: int = 8000) -> str:
    """Build KIE JSON extraction prompt, optionally grounded with Indra OCR output."""
    parts = [
        "Extract key information in the image.",
        "Return ONLY valid JSON following this exact schema:",
        SCHEMA_TEMPLATE,
        "Rules:",
        "- Use null for missing scalar fields and [] if no line items exist.",
        "- Normalize dates to YYYY-MM-DD when unambiguous.",
        "- Output plain JSON numbers without currency symbols for amounts and quantities.",
        "- Convert localized numbers carefully (e.g. '1.285,20' -> 1285.2, '1,234.56' -> 1234.56; "
        "for whole-unit currencies where '.000' or ',000' marks thousands like '60.000', "
        "output 60000).",
        "- Put a 3-letter ISO 4217 code in currency when identifiable (USD, EUR, MYR, IDR, GBP).",
        "- Do not invent values not present in the document.",
    ]
    if ocr_text and ocr_text.strip():
        clipped = ocr_text.strip()
        if len(clipped) > max_ocr_chars:
            half = max_ocr_chars // 2
            clipped = f"{clipped[:half]}\n...\n{clipped[-half:]}"
        parts.append("\nOCR transcript (for exact character verification):\n" + clipped)
    return "\n".join(parts)
