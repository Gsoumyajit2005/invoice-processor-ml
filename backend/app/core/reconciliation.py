"""Arithmetic consistency and escalation checks over extracted invoice fields."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.core.schemas import InvoiceExtraction

_TAX_INCL_RE = re.compile(
    r"\b(?:incl\.?(?:uding)?\s*(?:gst|vat|tax|mwst)|tax\s*included|gst\s*incl)\b",
    re.IGNORECASE,
)


class ReconciliationResult(BaseModel):
    """Outcome of arithmetic checks between line items, subtotal, tax, discount, and total."""

    items_sum: float | None = None
    items_match_subtotal: bool | None = None
    totals_reconcile: bool | None = None
    needs_escalation: bool = False
    warnings: list[str] = Field(default_factory=list)


def _close(a: float, b: float, *, rel_tol: float, abs_tol: float) -> bool:
    tol = max(abs_tol, rel_tol * max(abs(a), abs(b), 1.0))
    return abs(a - b) <= tol


def reconcile_invoice(
    data: InvoiceExtraction,
    *,
    ocr_text: str | None = None,
    rel_tol: float = 0.02,
    abs_tol: float = 0.15,
) -> ReconciliationResult:
    """Validate line-item sums and header total math, deciding escalation eligibility."""
    warnings: list[str] = []

    item_totals = [it.total_price for it in data.line_items if it.total_price is not None]
    items_sum = round(sum(item_totals), 4) if item_totals else None

    for idx, it in enumerate(data.line_items):
        if it.quantity is not None and it.unit_price is not None and it.total_price is not None:
            product = round(it.quantity * it.unit_price, 4)
            if not _close(product, it.total_price, rel_tol=rel_tol, abs_tol=abs_tol):
                warnings.append(
                    f"line_items[{idx}] qty*unit ({product}) != total_price ({it.total_price})"
                )

    items_match: bool | None = None
    if items_sum is not None:
        ref = data.subtotal if data.subtotal is not None else data.total_amount
        if ref is not None:
            items_match = _close(items_sum, ref, rel_tol=rel_tol, abs_tol=abs_tol)
            if not items_match:
                warnings.append(f"items_sum ({items_sum}) != reference subtotal/total ({ref})")

    totals_reconcile: bool | None = None
    if data.total_amount is not None:
        base = data.subtotal if data.subtotal is not None else items_sum
        if base is not None:
            tax = data.tax_amount or 0.0
            disc = abs(data.discount_amount or 0.0)
            candidates = [
                base + tax - disc,
                base + tax,
                base - disc,
            ]
            # Handle tax-inclusive receipts (e.g. Malaysian GST or European gross subtotals)
            if (
                tax > 0
                and data.subtotal is not None
                and _close(base - disc, data.total_amount, rel_tol=rel_tol, abs_tol=abs_tol)
                and ocr_text
                and _TAX_INCL_RE.search(ocr_text)
            ):
                totals_reconcile = True
            else:
                totals_reconcile = any(
                    _close(c, data.total_amount, rel_tol=rel_tol, abs_tol=abs_tol)
                    for c in candidates
                )
            if not totals_reconcile:
                warnings.append(
                    f"base ({base}) + tax ({tax}) - discount ({disc}) != "
                    f"total ({data.total_amount})"
                )

    missing_critical = data.total_amount is None or (
        data.vendor is None and data.receipt_number is None and not data.line_items
    )
    if data.total_amount is None:
        warnings.append("Missing total_amount")

    needs_escalation = bool(
        missing_critical or items_match is False or totals_reconcile is False
    )

    return ReconciliationResult(
        items_sum=items_sum,
        items_match_subtotal=items_match,
        totals_reconcile=totals_reconcile,
        needs_escalation=needs_escalation,
        warnings=warnings,
    )
