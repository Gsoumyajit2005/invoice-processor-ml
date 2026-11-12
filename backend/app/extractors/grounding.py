"""Visual grounding: fuzzy-match extracted fields back onto Indra OCR bounding boxes."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from rapidfuzz import fuzz

from app.core.schemas import BoundingBox, FieldProvenance, InvoiceExtraction
from app.extractors.base import OcrLine

_TOP_PREFER_FIELDS = {"vendor", "vendor_address", "receipt_number", "date", "bill_to"}
_BOTTOM_PREFER_FIELDS = {"subtotal", "tax_amount", "discount_amount", "total_amount"}
_PROVENANCE_FIELDS = (
    "vendor",
    "vendor_address",
    "receipt_number",
    "date",
    "due_date",
    "subtotal",
    "tax_amount",
    "discount_amount",
    "total_amount",
    "bill_to",
)

_INVOICE_NUM_PATTERNS = [
    re.compile(
        r"(?:invoice\s*(?:no\.?|num\.?|number|#)|tax\s*invoice\s*(?:no\.?|num\.?|#)|inv\s*(?:no\.?|#)|bill\s*(?:no\.?|#)|proforma\s*(?:invoice\s*)?(?:no\.?|num\.?|#)?|challan\s*(?:no\.?|#)?|rechnungs?-?nr\.?|bestellung\s*(?:aufnr)?)\s*[:#.\-\s]\s*([a-zA-Z0-9\-\/]+)",
        re.IGNORECASE,
    ),
    re.compile(r"\bproforma\s*(?:invoice\s*)?no\.?[^0-9a-zA-Z]*([a-zA-Z0-9\-\/]{2,20})", re.IGNORECASE),
    re.compile(r"\bproforma\s*no\.?.*?\b([0-9]{2,10})\b", re.IGNORECASE),
    re.compile(r"\b(?:invoice|rechnung|proforma)\s*#\s*([a-zA-Z0-9\-\/]+)", re.IGNORECASE),
    re.compile(r"\bAUFNR\s*([0-9]+)\b", re.IGNORECASE),
]
_DATE_LIKE_RE = re.compile(r"^(\d{1,4}[./-]\d{1,2}[./-]\d{1,4})$")
_TAX_ID_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$", re.IGNORECASE)


def _recover_receipt_number_from_ocr(ocr_lines: list[OcrLine]) -> str | None:
    """Intelligently recover missing invoice/receipt numbers directly from OCR transcript."""
    sorted_lines = sorted(ocr_lines, key=lambda l: (l.page, l.y1))
    for line in sorted_lines:
        if line.page > 1 or line.y1 > 700:
            continue
        for pat in _INVOICE_NUM_PATTERNS:
            m = pat.search(line.text)
            if m:
                cand = m.group(1).strip()
                if len(cand) < 3 or len(cand) > 35:
                    continue
                if _DATE_LIKE_RE.match(cand) or _TAX_ID_RE.match(cand):
                    continue
                if cand.lower() in {
                    "date",
                    "invoice",
                    "number",
                    "tax",
                    "total",
                    "proforma",
                    "challan",
                    "proformano",
                    "challanno",
                }:
                    continue
                return cand
    return None


def _find_candidate_span(
    line_text: str,
    candidates: list[str],
    *,
    is_numeric: bool,
) -> tuple[int, int] | None:
    """Find the best matching character span (start_idx, end_idx) of a candidate in line_text."""
    if not line_text or not candidates:
        return None

    line_lower = line_text.lower()

    # 1. Exact substring match in line_text (case-insensitive)
    for cand in candidates:
        cand_str = cand.strip()
        if not cand_str:
            continue
        idx = line_lower.find(cand_str.lower())
        if idx != -1:
            return (idx, idx + len(cand_str))

    # 2. For numeric fields: search for digits-and-punctuation tokens
    if is_numeric:
        for cand in candidates:
            cand_digits = re.sub(r"\D", "", cand)
            if not cand_digits:
                continue
            for m in re.finditer(r"[\d.,]+", line_text):
                token_digits = re.sub(r"\D", "", m.group(0))
                if token_digits == cand_digits:
                    return (m.start(), m.end())

    # 3. For multi-word text: search for tokens in sequence
    for cand in candidates:
        words = [w for w in re.split(r"\s+", cand.strip()) if w]
        if len(words) > 1:
            first_idx = line_lower.find(words[0].lower())
            if first_idx != -1:
                last_idx = line_lower.find(words[-1].lower(), first_idx)
                if last_idx != -1:
                    return (first_idx, last_idx + len(words[-1]))

    return None


def _interpolate_substring_bbox(
    line: OcrLine,
    start_char: int,
    end_char: int,
) -> BoundingBox:
    """Interpolate a tight sub-bounding box for substring [start_char..end_char] within an OcrLine."""
    text_len = len(line.text)
    if text_len == 0 or start_char >= end_char:
        return _line_to_bbox(line)

    start_char = max(0, min(start_char, text_len))
    end_char = max(start_char + 1, min(end_char, text_len))

    line_w = max(0.0, line.x2 - line.x1)

    # Linear character interpolation across [0..1000] coordinate space
    sub_x1 = line.x1 + line_w * (start_char / text_len)
    sub_x2 = line.x1 + line_w * (end_char / text_len)

    # Apply small padding (up to 3 units or 1.5% of line width) without exceeding original bounds
    pad = min(3.0, line_w * 0.015)
    x1 = max(line.x1, sub_x1 - pad)
    x2 = min(line.x2, sub_x2 + pad)

    return BoundingBox(
        page=line.page,
        x1=round(x1, 1),
        y1=line.y1,
        x2=round(x2, 1),
        y2=line.y2,
        confidence=line.confidence,
    )


def _norm_str(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _money_variants(amount: float) -> list[str]:
    abs_val = abs(amount)
    us_2 = f"{abs_val:,.2f}"
    plain_2 = f"{abs_val:.2f}"
    plain_int = f"{int(round(abs_val))}" if abs(abs_val - round(abs_val)) < 1e-6 else plain_2
    eu_2 = us_2.replace(",", "_").replace(".", ",").replace("_", ".")
    eu_plain = plain_2.replace(".", ",")
    variants = [plain_2, us_2, eu_2, eu_plain, plain_int]
    # Deduplicate while preserving order
    return list(dict.fromkeys(v for v in variants if v))


def _date_variants(iso_date: str) -> list[str]:
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
    except ValueError:
        return [iso_date]
    return list(
        dict.fromkeys(
            [
                iso_date,
                dt.strftime("%d.%m.%Y"),
                dt.strftime("%d/%m/%Y"),
                dt.strftime("%m/%d/%Y"),
                dt.strftime("%d-%m-%Y"),
                dt.strftime("%d %b %Y"),
                dt.strftime("%b %d, %Y"),
                dt.strftime("%Y/%m/%d"),
            ]
        )
    )


def _candidate_strings(field: str, value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (int, float)):
        return _money_variants(float(value))
    if field in {"date", "due_date"} and isinstance(value, str):
        return _date_variants(value)
    text = str(value).strip()
    return [text] if text else []


def _line_to_bbox(line: OcrLine) -> BoundingBox:
    return BoundingBox(
        page=line.page,
        x1=line.x1,
        y1=line.y1,
        x2=line.x2,
        y2=line.y2,
        confidence=line.confidence,
    )


def _score_line(
    query: str,
    line_text: str,
    *,
    is_numeric: bool,
) -> float:
    if not query or not line_text:
        return 0.0
    if is_numeric:
        compact_line = line_text.replace(" ", "")
        if query in compact_line:
            # Prefer exact token match over substring embedded in long serial numbers
            if re.search(rf"(?<![0-9]){re.escape(query)}(?![0-9])", compact_line):
                return 100.0
            return 85.0
        return 0.0

    q_norm = _norm_str(query)
    l_norm = _norm_str(line_text)
    if not q_norm or not l_norm:
        return 0.0
    if q_norm == l_norm:
        return 100.0
    if q_norm in l_norm:
        return 96.0
    if len(q_norm) <= 4:
        return float(fuzz.ratio(q_norm, l_norm))
    return float(max(fuzz.token_set_ratio(q_norm, l_norm), fuzz.partial_ratio(q_norm, l_norm)))


def _match_field_bbox(
    field: str,
    value: Any,
    ocr_lines: list[OcrLine],
) -> BoundingBox | None:
    if value is None or not ocr_lines:
        return None
    candidates = _candidate_strings(field, value)
    if not candidates:
        return None

    is_numeric = isinstance(value, (int, float))
    min_score = 92.0 if is_numeric else (85.0 if field == "receipt_number" else 76.0)

    best_score = -1.0
    best_line: OcrLine | None = None

    for line in ocr_lines:
        line_score = max(
            _score_line(cand, line.text, is_numeric=is_numeric) for cand in candidates
        )
        if line_score < min_score:
            continue

        # Positional tie-breaker: amounts near bottom, headers near top
        pos_bias = 0.0
        if field in _BOTTOM_PREFER_FIELDS:
            pos_bias = (line.y1 / 1000.0) * 1.5
        elif field in _TOP_PREFER_FIELDS:
            pos_bias = ((1000.0 - line.y1) / 1000.0) * 1.5

        adjusted = line_score + pos_bias
        if adjusted > best_score:
            best_score = adjusted
            best_line = line

    if best_line is None:
        return None

    span = _find_candidate_span(best_line.text, candidates, is_numeric=is_numeric)
    if span is not None:
        return _interpolate_substring_bbox(best_line, span[0], span[1])

    return _line_to_bbox(best_line)


def _match_line_item_bbox(
    description: str,
    total_price: float | None,
    ocr_lines: list[OcrLine],
) -> BoundingBox | None:
    if not description or not ocr_lines:
        return None
    q_norm = _norm_str(description)
    if not q_norm:
        return None

    best_score = -1.0
    anchor: OcrLine | None = None
    for line in ocr_lines:
        score = _score_line(description, line.text, is_numeric=False)
        if score >= 74.0 and score > best_score:
            best_score = score
            anchor = line

    if anchor is None:
        return None

    desc_span = _find_candidate_span(anchor.text, [description], is_numeric=False)
    desc_bbox = (
        _interpolate_substring_bbox(anchor, desc_span[0], desc_span[1])
        if desc_span is not None
        else _line_to_bbox(anchor)
    )

    if total_price is None:
        return desc_bbox

    price_variants = _money_variants(total_price)

    # Check if total_price is on the same line as anchor
    same_line_price_span = _find_candidate_span(anchor.text, price_variants, is_numeric=True)
    if same_line_price_span is not None:
        min_start = min(desc_span[0] if desc_span else 0, same_line_price_span[0])
        max_end = max(desc_span[1] if desc_span else len(anchor.text), same_line_price_span[1])
        return _interpolate_substring_bbox(anchor, min_start, max_end)

    # Expand across same-row price cell when total_price shares the horizontal row band
    row_mid_y = (anchor.y1 + anchor.y2) * 0.5
    row_height = max(anchor.y2 - anchor.y1, 12.0)
    for other in ocr_lines:
        if other.page != anchor.page:
            continue
        other_mid_y = (other.y1 + other.y2) * 0.5
        if abs(other_mid_y - row_mid_y) > row_height * 0.9:
            continue
        if any(_score_line(pv, other.text, is_numeric=True) >= 92.0 for pv in price_variants):
            other_price_span = _find_candidate_span(other.text, price_variants, is_numeric=True)
            other_bbox = (
                _interpolate_substring_bbox(other, other_price_span[0], other_price_span[1])
                if other_price_span is not None
                else _line_to_bbox(other)
            )
            return BoundingBox(
                page=anchor.page,
                x1=min(desc_bbox.x1, other_bbox.x1),
                y1=min(desc_bbox.y1, other_bbox.y1),
                x2=max(desc_bbox.x2, other_bbox.x2),
                y2=max(desc_bbox.y2, other_bbox.y2),
                confidence=round((anchor.confidence + other.confidence) / 2.0, 4),
            )

    return desc_bbox


def ground_extraction(
    extraction: InvoiceExtraction,
    ocr_lines: list[OcrLine],
) -> InvoiceExtraction:
    """Attach OCR-matched BoundingBoxes and provenance metadata to extracted fields."""
    # Fallback: if receipt_number is missing, attempt pattern recovery from OCR text
    if not extraction.receipt_number:
        recovered = _recover_receipt_number_from_ocr(ocr_lines)
        if recovered:
            extraction = extraction.model_copy(update={"receipt_number": recovered})

    provenance: dict[str, FieldProvenance] = dict(extraction.provenance)

    for field_name in _PROVENANCE_FIELDS:
        val = getattr(extraction, field_name)
        if val is None:
            continue
        bbox = _match_field_bbox(field_name, val, ocr_lines)
        provenance[field_name] = FieldProvenance(
            value=val,
            bbox=bbox,
            source="ocr_matched" if bbox is not None else "vlm_inferred",
        )

    grounded_items = []
    for item in extraction.line_items:
        item_bbox = item.bbox or _match_line_item_bbox(
            item.description, item.total_price, ocr_lines
        )
        grounded_items.append(item.model_copy(update={"bbox": item_bbox}))

    return extraction.model_copy(
        update={"provenance": provenance, "line_items": grounded_items}
    )
