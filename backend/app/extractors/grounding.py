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

    return _line_to_bbox(best_line) if best_line else None


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

    bbox = _line_to_bbox(anchor)
    if total_price is None:
        return bbox

    # Expand across same-row price cell when total_price shares the horizontal row band
    price_variants = _money_variants(total_price)
    row_mid_y = (anchor.y1 + anchor.y2) * 0.5
    row_height = max(anchor.y2 - anchor.y1, 12.0)
    for other in ocr_lines:
        if other.page != anchor.page:
            continue
        other_mid_y = (other.y1 + other.y2) * 0.5
        if abs(other_mid_y - row_mid_y) > row_height * 0.9:
            continue
        if any(_score_line(pv, other.text, is_numeric=True) >= 92.0 for pv in price_variants):
            bbox = BoundingBox(
                page=anchor.page,
                x1=min(bbox.x1, other.x1),
                y1=min(bbox.y1, other.y1),
                x2=max(bbox.x2, other.x2),
                y2=max(bbox.y2, other.y2),
                confidence=round((anchor.confidence + other.confidence) / 2.0, 4),
            )
            break
    return bbox


def ground_extraction(
    extraction: InvoiceExtraction,
    ocr_lines: list[OcrLine],
) -> InvoiceExtraction:
    """Attach OCR-matched BoundingBoxes and provenance metadata to extracted fields."""
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
