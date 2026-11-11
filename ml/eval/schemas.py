"""Canonical structured extraction schemas and JSON/numeric normalization helpers."""

from __future__ import annotations

from typing import Any

from app.core.schemas import (
    clean_optional_str,
    extract_json_object,
)
from app.core.schemas import parse_money as _backend_parse_money
from pydantic import BaseModel, Field, field_validator


def parse_money(value: Any) -> float | None:
    """Parse common monetary string formats into float, returning None when unparseable."""
    return _backend_parse_money(value, strict=False)


class LineItem(BaseModel):
    """Single invoice or receipt line item."""

    description: str
    quantity: float | None = None
    unit_price: float | None = None
    total_price: float | None = None

    @field_validator("description", mode="before")
    @classmethod
    def _clean_description(cls, value: Any) -> str:
        return clean_optional_str(value) or ""

    @field_validator("quantity", "unit_price", "total_price", mode="before")
    @classmethod
    def _parse_numeric(cls, value: Any) -> float | None:
        return parse_money(value)


class InvoiceExtraction(BaseModel):
    """Unified structured extraction schema used across baselines and VLM candidates."""

    vendor: str | None = None
    vendor_address: str | None = None
    receipt_number: str | None = None
    date: str | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    discount_amount: float | None = None
    total_amount: float | None = None
    bill_to: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)

    @field_validator(
        "vendor",
        "vendor_address",
        "receipt_number",
        "date",
        "currency",
        "bill_to",
        mode="before",
    )
    @classmethod
    def _clean_str_field(cls, value: Any) -> str | None:
        return clean_optional_str(value)

    @field_validator(
        "subtotal",
        "tax_amount",
        "discount_amount",
        "total_amount",
        mode="before",
    )
    @classmethod
    def _clean_money_field(cls, value: Any) -> float | None:
        return parse_money(value)

    @field_validator("line_items", mode="before")
    @classmethod
    def _clean_items(cls, value: Any) -> list[Any]:
        if not value or not isinstance(value, list):
            return []
        return [
            item
            for item in value
            if isinstance(item, (dict, LineItem))
            and (
                item.description
                if isinstance(item, LineItem)
                else clean_optional_str(item.get("description"))
            )
        ]


class ExtractionValidation(BaseModel):
    """Arithmetic consistency checks over extracted amounts and line items."""

    items_sum: float | None = None
    items_match_subtotal: bool | None = None
    totals_reconcile: bool | None = None

    @classmethod
    def check(
        cls, data: InvoiceExtraction, rel_tol: float = 0.02, abs_tol: float = 0.15
    ) -> ExtractionValidation:
        """Compute line-item sum and subtotal/tax/discount/total reconciliation flags."""
        item_totals = [it.total_price for it in data.line_items if it.total_price is not None]
        items_sum = round(sum(item_totals), 4) if item_totals else None

        def close(a: float, b: float) -> bool:
            tol = max(abs_tol, rel_tol * max(abs(a), abs(b), 1.0))
            return abs(a - b) <= tol

        items_match = None
        if items_sum is not None:
            ref = data.subtotal if data.subtotal is not None else data.total_amount
            if ref is not None:
                items_match = close(items_sum, ref)

        totals_reconcile = None
        if data.total_amount is not None:
            base = data.subtotal if data.subtotal is not None else items_sum
            if base is not None:
                tax = data.tax_amount or 0.0
                disc = data.discount_amount or 0.0
                # Discount is stored positive here, though some models emit negative discount.
                expected_sub = base + tax - abs(disc)
                expected_no_disc = base + tax
                totals_reconcile = close(expected_sub, data.total_amount) or close(
                    expected_no_disc, data.total_amount
                )

        return cls(
            items_sum=items_sum,
            items_match_subtotal=items_match,
            totals_reconcile=totals_reconcile,
        )


def parse_extraction_output(raw_text: str) -> tuple[InvoiceExtraction | None, bool, str | None]:
    """Parse raw model text into a validated InvoiceExtraction object."""
    payload, err = extract_json_object(raw_text)
    if payload is None:
        return None, False, err
    try:
        model = InvoiceExtraction.model_validate(payload)
        return model, True, None
    except Exception as exc:  # noqa: BLE001
        return None, False, f"pydantic_validation_error: {exc}"
