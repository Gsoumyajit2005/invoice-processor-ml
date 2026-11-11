"""Canonical Pydantic schemas, localized parsers, and API DTOs."""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from dateutil import parser as date_parser
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_NULL_LITERALS = {"null", "none", "n/a", "na", "-", "--", "unknown", ""}
_CURRENCY_RE = re.compile(
    r"(?:US\$|RM|Rp|CHF|EUR|USD|MYR|IDR|GBP|SGD|AUD|CAD|INR|[\$€£¥₹])",
    re.IGNORECASE,
)
_SYMBOL_TO_ISO = {
    "$": "USD",
    "US$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "RM": "MYR",
    "RP": "IDR",
    "¥": "JPY",
}
_ISO_DATE_RE = re.compile(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$")
_DOT_DATE_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$")
_SLASH_OR_DASH_DATE_RE = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$")

# Month name translations for European invoices (German / French / Spanish common headers)
_EURO_MONTHS = {
    "januar": "January",
    "februar": "February",
    "märz": "March",
    "maerz": "March",
    "mai": "May",
    "juni": "June",
    "juli": "July",
    "oktober": "October",
    "dezember": "December",
}


def clean_optional_str(value: Any) -> str | None:
    """Normalize blank or null-like values into None."""
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text.lower() in _NULL_LITERALS:
        return None
    return text


def parse_money(value: Any, *, strict: bool = True) -> float | None:
    """Parse localized monetary or numeric inputs into a finite float.

    Examples:
        "1.285,20" -> 1285.2
        "1,234.56" -> 1234.56
        "Rp 60.000" -> 60000.0
        "(45.00)" -> -45.0
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"Boolean is not a valid numeric amount: {value!r}")
    if isinstance(value, (int, float)):
        num = float(value)
        if not math.isfinite(num):
            raise ValueError(f"Amount must be finite: {value!r}")
        return num

    raw = str(value).strip()
    if raw.lower() in _NULL_LITERALS:
        return None

    is_whole_unit_ccy = bool(re.search(r"(?:^|\b)(?:rp\.?|idr)(?:\b|\d)", raw, re.IGNORECASE))
    text = raw
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    if text.startswith("-"):
        negative = True
        text = text[1:].strip()
    elif text.endswith("-"):
        negative = True
        text = text[:-1].strip()

    text = _CURRENCY_RE.sub("", text).replace(" ", "").replace("\u00a0", "")
    cleaned = re.sub(r"[^0-9.,]", "", text)
    if not cleaned:
        if strict:
            raise ValueError(f"Invalid numeric value: {value!r}")
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit() and int(parts[0]) >= 1:
            cleaned = "".join(parts)
        elif len(parts) == 2:
            cleaned = f"{parts[0]}.{parts[1]}"
        else:
            cleaned = (
                "".join(parts[:-1]) + f".{parts[-1]}"
                if len(parts[-1]) in (1, 2)
                else "".join(parts)
            )
    elif "." in cleaned:
        parts = cleaned.split(".")
        if (
            is_whole_unit_ccy
            and len(parts) == 2
            and len(parts[1]) == 3
            and parts[0].isdigit()
            and int(parts[0]) >= 1
        ):
            cleaned = "".join(parts)
        elif len(parts) > 2:
            cleaned = (
                "".join(parts[:-1]) + f".{parts[-1]}"
                if len(parts[-1]) in (1, 2)
                else "".join(parts)
            )

    try:
        num = float(cleaned)
    except ValueError as exc:
        if strict:
            raise ValueError(f"Invalid numeric value: {value!r}") from exc
        return None

    if not math.isfinite(num):
        raise ValueError(f"Non-finite amount: {value!r}")
    return -num if negative else num


def normalize_currency(value: Any) -> str | None:
    """Normalize currency symbols or strings to an uppercase 3-letter ISO code when known."""
    text = clean_optional_str(value)
    if text is None:
        return None
    upper = text.upper()
    if upper in _SYMBOL_TO_ISO:
        return _SYMBOL_TO_ISO[upper]
    letters = re.sub(r"[^A-Z]", "", upper)
    if len(letters) == 3:
        return letters
    return upper[:8]


def normalize_date(value: Any) -> str | None:
    """Normalize ISO, US, European (DD.MM.YYYY), and text dates into YYYY-MM-DD."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = clean_optional_str(value)
    if text is None:
        return None

    iso_m = _ISO_DATE_RE.match(text)
    if iso_m:
        y, m, d = int(iso_m.group(1)), int(iso_m.group(2)), int(iso_m.group(3))
        return date(y, m, d).isoformat()

    dot_m = _DOT_DATE_RE.match(text)
    if dot_m:
        d, m, y = int(dot_m.group(1)), int(dot_m.group(2)), int(dot_m.group(3))
        if y < 100:
            y += 2000 if y < 70 else 1900
        return date(y, m, d).isoformat()

    slash_m = _SLASH_OR_DASH_DATE_RE.match(text)
    if slash_m:
        p1, p2, y = int(slash_m.group(1)), int(slash_m.group(2)), int(slash_m.group(3))
        if y < 100:
            y += 2000 if y < 70 else 1900
        # Prefer day-first unless second component clearly represents the day (>12)
        day_first = not (p1 <= 12 and p2 > 12)
        d, m = (p1, p2) if day_first else (p2, p1)
        return date(y, m, d).isoformat()

    translated = text
    for foreign, eng in _EURO_MONTHS.items():
        translated = re.sub(rf"\b{foreign}\b", eng, translated, flags=re.IGNORECASE)

    try:
        parsed = date_parser.parse(translated, dayfirst=True, fuzzy=False)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"Unrecognized date format: {value!r}") from exc
    return parsed.date().isoformat()


class BoundingBox(BaseModel):
    """Normalized [0..1000] bounding box anchored to a 1-indexed document page."""

    page: int = Field(default=1, ge=1)
    x1: float = Field(ge=0.0, le=1000.0)
    y1: float = Field(ge=0.0, le=1000.0)
    x2: float = Field(ge=0.0, le=1000.0)
    y2: float = Field(ge=0.0, le=1000.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_order(self) -> BoundingBox:
        if self.x2 < self.x1:
            self.x1, self.x2 = self.x2, self.x1
        if self.y2 < self.y1:
            self.y1, self.y2 = self.y2, self.y1
        return self


class FieldProvenance(BaseModel):
    """Provenance record tying an extracted scalar field back to OCR coordinates."""

    value: Any
    bbox: BoundingBox | None = None
    source: Literal["ocr_matched", "vlm_inferred", "user_edited"] = "vlm_inferred"


class LineItemSchema(BaseModel):
    """Canonical invoice or receipt line item."""

    description: str
    quantity: float | None = None
    unit_price: float | None = None
    total_price: float | None = None
    bbox: BoundingBox | None = None

    @field_validator("description", mode="before")
    @classmethod
    def _clean_description(cls, value: Any) -> str:
        return clean_optional_str(value) or ""

    @field_validator("quantity", "unit_price", "total_price", mode="before")
    @classmethod
    def _clean_numbers(cls, value: Any) -> float | None:
        return parse_money(value, strict=True)


class InvoiceExtraction(BaseModel):
    """Unified structured extraction schema for API, DB provenance, and evaluators."""

    document_type: Literal["invoice", "receipt", "credit_note", "unknown"] = "invoice"
    vendor: str | None = None
    vendor_address: str | None = None
    receipt_number: str | None = None
    date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    discount_amount: float | None = None
    total_amount: float | None = None
    bill_to: str | None = None
    line_items: list[LineItemSchema] = Field(default_factory=list)
    provenance: dict[str, FieldProvenance] = Field(default_factory=dict)
    validation_warnings: list[str] = Field(default_factory=list)

    @field_validator("document_type", mode="before")
    @classmethod
    def _clean_doc_type(cls, value: Any) -> str:
        cleaned = (clean_optional_str(value) or "invoice").lower().replace(" ", "_")
        if cleaned in {"invoice", "receipt", "credit_note", "unknown"}:
            return cleaned
        return "invoice"

    @field_validator("vendor", "vendor_address", "receipt_number", "bill_to", mode="before")
    @classmethod
    def _clean_text_fields(cls, value: Any) -> str | None:
        return clean_optional_str(value)

    @field_validator("currency", mode="before")
    @classmethod
    def _clean_currency(cls, value: Any) -> str | None:
        return normalize_currency(value)

    @field_validator("date", "due_date", mode="before")
    @classmethod
    def _clean_dates(cls, value: Any) -> str | None:
        return normalize_date(value)

    @field_validator(
        "subtotal", "tax_amount", "discount_amount", "total_amount", mode="before"
    )
    @classmethod
    def _clean_amounts(cls, value: Any) -> float | None:
        return parse_money(value, strict=True)

    @field_validator("line_items", mode="before")
    @classmethod
    def _clean_items(cls, value: Any) -> list[Any]:
        if not value or not isinstance(value, list):
            return []
        return [
            item
            for item in value
            if isinstance(item, (dict, LineItemSchema))
            and (
                item.description
                if isinstance(item, LineItemSchema)
                else clean_optional_str(item.get("description"))
            )
        ]


def extract_json_object(raw_text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Extract a JSON object from model text, stripping <think> and markdown fences."""
    text = _THINK_RE.sub("", raw_text or "").strip()
    fence_match = _FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed, None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        return None, "no_json_object_found"

    depth = 0
    in_str = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : idx + 1]
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        return parsed, None
                    return None, "json_not_object"
                except json.JSONDecodeError as exc:
                    return None, f"json_decode_error: {exc}"

    return None, "unclosed_json_object"


def parse_vlm_extraction(
    raw_text: str,
) -> tuple[InvoiceExtraction | None, bool, str | None]:
    """Parse raw model output into InvoiceExtraction, recording any field-level warnings."""
    payload, err = extract_json_object(raw_text)
    if payload is None:
        return None, False, err

    try:
        return InvoiceExtraction.model_validate(payload), True, None
    except ValidationError as exc:
        # Recover partial extraction if only optional date/numeric formatting had noisy text,
        # while explicitly recording warnings instead of silently discarding errors.
        warnings: list[str] = []
        sanitized = dict(payload)
        for error in exc.errors():
            loc = error.get("loc", ())
            if len(loc) == 1 and isinstance(loc[0], str):
                field = loc[0]
                if field in {"date", "due_date"}:
                    warnings.append(f"{field}: {error.get('msg')} (raw={sanitized.get(field)!r})")
                    sanitized[field] = None
                elif field in {"subtotal", "tax_amount", "discount_amount", "total_amount"}:
                    warnings.append(f"{field}: {error.get('msg')} (raw={sanitized.get(field)!r})")
                    sanitized[field] = None
        if warnings:
            try:
                model = InvoiceExtraction.model_validate(sanitized)
                model.validation_warnings.extend(warnings)
                return model, True, None
            except ValidationError as retry_exc:
                return None, False, f"pydantic_validation_error: {retry_exc}"
        return None, False, f"pydantic_validation_error: {exc}"


# --- API Request / Response Schemas ---


class LineItemDTO(LineItemSchema):
    """Line item returned by API endpoints."""

    id: UUID | None = None
    position: int = 0


class ExtractionResponse(BaseModel):
    """Response returned by POST /api/v1/extract and batch items."""

    invoice_id: UUID
    filename: str
    file_hash: str
    semantic_hash: str | None = None
    duplicate_of_id: UUID | None = None
    status: Literal["extracted", "needs_review", "verified", "failed"]
    extractor_used: str
    latency_ms: int
    page_count: int
    items_match_subtotal: bool | None = None
    totals_reconcile: bool | None = None
    needs_escalation: bool = False
    extraction: InvoiceExtraction
    page_image_urls: list[str] = Field(default_factory=list)
    created_at: datetime


class InvoiceSummary(BaseModel):
    """Compact invoice row used for paginated GET /api/v1/invoices."""

    id: UUID
    filename: str
    document_type: str
    vendor: str | None = None
    receipt_number: str | None = None
    date: str | None = None
    currency: str | None = None
    total_amount: float | None = None
    status: str
    extractor_used: str | None = None
    items_match_subtotal: bool | None = None
    totals_reconcile: bool | None = None
    duplicate_of_id: UUID | None = None
    page_count: int
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseModel):
    """Paginated invoice list response."""

    items: list[InvoiceSummary]
    total: int
    limit: int
    offset: int


class InvoiceDetailResponse(BaseModel):
    """Full invoice inspection payload for Workbench UI."""

    id: UUID
    filename: str
    file_hash: str
    semantic_hash: str | None = None
    duplicate_of_id: UUID | None = None
    status: str
    document_type: str
    vendor: str | None = None
    vendor_address: str | None = None
    receipt_number: str | None = None
    date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    discount_amount: float | None = None
    total_amount: float | None = None
    bill_to: str | None = None
    extractor_used: str | None = None
    extraction_latency_ms: int | None = None
    items_match_subtotal: bool | None = None
    totals_reconcile: bool | None = None
    page_count: int
    raw_ocr_markdown: str | None = None
    provenance: dict[str, FieldProvenance] = Field(default_factory=dict)
    validation_warnings: list[str] = Field(default_factory=list)
    line_items: list[LineItemDTO] = Field(default_factory=list)
    page_image_urls: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class InvoicePatchRequest(BaseModel):
    """HITL review / correction payload for PATCH /api/v1/invoices/{id}."""

    document_type: Literal["invoice", "receipt", "credit_note", "unknown"] | None = None
    vendor: str | None = None
    vendor_address: str | None = None
    receipt_number: str | None = None
    date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    discount_amount: float | None = None
    total_amount: float | None = None
    bill_to: str | None = None
    line_items: list[LineItemSchema] | None = None
    status: Literal["extracted", "needs_review", "verified", "failed"] | None = None
    mark_verified: bool = False

    @field_validator("vendor", "vendor_address", "receipt_number", "bill_to", mode="before")
    @classmethod
    def _clean_text_fields(cls, value: Any) -> str | None:
        return clean_optional_str(value)

    @field_validator("currency", mode="before")
    @classmethod
    def _clean_currency(cls, value: Any) -> str | None:
        return normalize_currency(value)

    @field_validator("date", "due_date", mode="before")
    @classmethod
    def _clean_dates(cls, value: Any) -> str | None:
        return normalize_date(value)

    @field_validator(
        "subtotal", "tax_amount", "discount_amount", "total_amount", mode="before"
    )
    @classmethod
    def _clean_amounts(cls, value: Any) -> float | None:
        return parse_money(value, strict=True)


class BulkReportRequest(BaseModel):
    """Filter or explicit IDs for bulk export."""

    invoice_ids: list[UUID] | None = None
    status: str | None = None
    format: Literal["json", "csv", "html"] = "json"
