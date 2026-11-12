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


def normalize_extraction_scales(data: InvoiceExtraction) -> InvoiceExtraction:
    """Detect and auto-correct power-of-10 decimal scaling errors in line items and totals.

    Common in European/German invoices where trailing decimal zeros (e.g. '16,0000 pro VE')
    or cents are misread by VLMs/OCR without decimal separators, yielding 100x, 1000x, or
    10000x arithmetic scale mismatches.
    """
    scale_powers = (100.0, 1000.0, 10000.0)
    warnings: list[str] = list(data.validation_warnings)
    updated_items = []
    has_item_changes = False

    for idx, it in enumerate(data.line_items):
        item = it
        if (
            it.quantity is not None
            and it.quantity > 0
            and it.unit_price is not None
            and it.unit_price > 0
            and it.total_price is not None
            and it.total_price > 0
        ):
            prod = it.quantity * it.unit_price
            ratio = prod / it.total_price

            # If already close, no scale error
            if abs(ratio - 1.0) <= 0.05:
                updated_items.append(item)
                continue

            fixed = False
            # Check if unit_price was inflated by 100x, 1000x, 10000x
            for scale in scale_powers:
                if abs(ratio - scale) / scale <= 0.05:
                    new_unit = round(it.unit_price / scale, 4)
                    item = item.model_copy(update={"unit_price": new_unit})
                    warnings.append(
                        f"Auto-scaled line item [{idx}] unit_price from {it.unit_price} to {new_unit} (resolved {int(scale)}x decimal scale)"
                    )
                    fixed = True
                    has_item_changes = True
                    break

            if not fixed:
                # Check if total_price was inflated by 100x, 1000x, 10000x
                inv_ratio = it.total_price / prod
                for scale in scale_powers:
                    if abs(inv_ratio - scale) / scale <= 0.05:
                        new_total = round(it.total_price / scale, 4)
                        item = item.model_copy(update={"total_price": new_total})
                        warnings.append(
                            f"Auto-scaled line item [{idx}] total_price from {it.total_price} to {new_total} (resolved {int(scale)}x decimal scale)"
                        )
                        fixed = True
                        has_item_changes = True
                        break

        updated_items.append(item)

    current_data = (
        data.model_copy(update={"line_items": updated_items}) if has_item_changes else data
    )

    # Check header totals against items_sum
    item_totals = [it.total_price for it in updated_items if it.total_price is not None]
    items_sum = round(sum(item_totals), 4) if item_totals else None

    new_subtotal = current_data.subtotal
    if new_subtotal is not None and new_subtotal > 0 and items_sum is not None and items_sum > 0:
        ratio = new_subtotal / items_sum
        if abs(ratio - 1.0) > 0.05:
            for scale in scale_powers:
                if abs(ratio - scale) / scale <= 0.05:
                    new_subtotal = round(new_subtotal / scale, 4)
                    warnings.append(
                        f"Auto-scaled subtotal from {current_data.subtotal} to {new_subtotal} (resolved {int(scale)}x decimal scale)"
                    )
                    break

    new_total = current_data.total_amount
    base_ref = new_subtotal if new_subtotal is not None else items_sum
    if new_total is not None and new_total > 0 and base_ref is not None and base_ref > 0:
        tax = current_data.tax_amount or 0.0
        disc = abs(current_data.discount_amount or 0.0)
        expected_total = base_ref + tax - disc
        if expected_total > 0:
            ratio = new_total / expected_total
            if abs(ratio - 1.0) > 0.05:
                for scale in scale_powers:
                    if abs(ratio - scale) / scale <= 0.05:
                        new_total = round(new_total / scale, 4)
                        warnings.append(
                            f"Auto-scaled total_amount from {current_data.total_amount} to {new_total} (resolved {int(scale)}x decimal scale)"
                        )
                        break

    return current_data.model_copy(
        update={
            "subtotal": new_subtotal,
            "total_amount": new_total,
            "validation_warnings": warnings,
        }
    )


def reconcile_invoice(
    data: InvoiceExtraction,
    *,
    ocr_text: str | None = None,
    rel_tol: float = 0.02,
    abs_tol: float = 0.15,
) -> ReconciliationResult:
    """Validate line-item sums and header total math, deciding escalation eligibility."""
    # Detect and resolve any decimal scaling anomalies before arithmetic checks
    normalized_data = normalize_extraction_scales(data)
    scale_warnings = [
        w for w in normalized_data.validation_warnings if w not in data.validation_warnings
    ]
    data = normalized_data

    warnings: list[str] = list(scale_warnings)

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
