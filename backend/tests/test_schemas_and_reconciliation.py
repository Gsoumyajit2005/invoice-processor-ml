"""Unit tests for localized schemas, non-silent errors, math reconciliation, and hashing."""

from __future__ import annotations

import pytest
from app.core.hashing import compute_file_hash, compute_semantic_hash
from app.core.reconciliation import normalize_extraction_scales, reconcile_invoice
from app.core.schemas import (
    InvoiceExtraction,
    LineItemSchema,
    normalize_currency,
    normalize_date,
    parse_money,
    parse_vlm_extraction,
)
from pydantic import ValidationError


def test_parse_money_handles_localized_formats_and_errors() -> None:
    assert parse_money("1.285,20") == 1285.2
    assert parse_money("1,234.56") == 1234.56
    assert parse_money("Rp 60.000") == 60000.0
    assert parse_money("(45.50)") == -45.5
    assert parse_money("N/A") is None
    assert parse_money(None) is None

    with pytest.raises(ValueError, match="Invalid numeric value"):
        parse_money("not-a-number")
    with pytest.raises(ValueError, match="finite"):
        parse_money(float("nan"))


def test_normalize_date_handles_eu_us_iso_and_text_formats() -> None:
    assert normalize_date("2026-01-27") == "2026-01-27"
    assert normalize_date("28.05.2025") == "2025-05-28"
    assert normalize_date("15/03/2024") == "2024-03-15"
    assert normalize_date("05/28/2025") == "2025-05-28"
    assert normalize_date("27 Jan 2026") == "2026-01-27"
    assert normalize_date("02. Mai 2022") == "2022-05-02"
    assert normalize_date("-") is None

    with pytest.raises(ValueError, match="Unrecognized date"):
        normalize_date("sometime next tuesday")


def test_normalize_currency() -> None:
    assert normalize_currency("€") == "EUR"
    assert normalize_currency("RM") == "MYR"
    assert normalize_currency("usd") == "USD"
    assert normalize_currency("") is None


def test_invoice_extraction_strict_vs_vlm_warning_recovery() -> None:
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate({"vendor": "ACME", "date": "bad-date", "total_amount": 10})

    raw_json = '{"vendor": "ACME", "date": "bad-date", "total_amount": "€ 12,50"}'
    ext, ok, err = parse_vlm_extraction(f"<think>reasoning</think>\n```json\n{raw_json}\n```")
    assert ok is True
    assert err is None
    assert ext is not None
    assert ext.vendor == "ACME"
    assert ext.date is None
    assert ext.total_amount == 12.5
    assert any("date:" in w for w in ext.validation_warnings)


def test_reconcile_invoice_detects_mismatches_and_gst_inclusive_receipts() -> None:
    ok_inv = InvoiceExtraction(
        vendor="Alpha",
        subtotal=100.0,
        tax_amount=19.0,
        discount_amount=10.0,
        total_amount=109.0,
        line_items=[
            LineItemSchema(description="Part A", quantity=2, unit_price=50, total_price=100)
        ],
    )
    res_ok = reconcile_invoice(ok_inv)
    assert res_ok.items_match_subtotal is True
    assert res_ok.totals_reconcile is True
    assert res_ok.needs_escalation is False

    bad_inv = ok_inv.model_copy(update={"total_amount": 999.0})
    res_bad = reconcile_invoice(bad_inv)
    assert res_bad.totals_reconcile is False
    assert res_bad.needs_escalation is True

    gst_incl = InvoiceExtraction(
        vendor="SWC",
        subtotal=8.0,
        tax_amount=0.45,
        total_amount=8.0,
        line_items=[LineItemSchema(description="20X30 1KG", total_price=8.0)],
    )
    res_incl = reconcile_invoice(gst_incl, ocr_text="Total (Incl. GST 6%): RM 8.00")
    assert res_incl.totals_reconcile is True
    assert res_incl.needs_escalation is False


def test_semantic_hash_requires_identifying_fields_and_is_order_stable() -> None:
    empty = InvoiceExtraction()
    assert compute_semantic_hash(empty) is None

    total_only = InvoiceExtraction(total_amount=50.0, date="2025-01-01")
    assert compute_semantic_hash(total_only) is None

    a = InvoiceExtraction(
        vendor="East Repair Inc.",
        receipt_number="US-001",
        date="2019-02-11",
        total_amount=154.06,
    )
    b = InvoiceExtraction(
        vendor="east repair inc",
        receipt_number="us001",
        date="2019-02-11",
        total_amount=154.0600,
    )
    c = a.model_copy(update={"total_amount": 155.00})
    assert compute_semantic_hash(a) == compute_semantic_hash(b)
    assert compute_semantic_hash(a) != compute_semantic_hash(c)
    assert len(compute_file_hash(b"hello")) == 64


def test_parse_money_european_decimals_and_units() -> None:
    assert parse_money("16,0000") == 16.0
    assert parse_money("64,00") == 64.0
    assert parse_money("16,0000 pro 1 VE") == 16.0
    assert parse_money("0,4500 €") == 0.45
    assert parse_money("12,50 EUR / Stk.") == 12.5


def test_invoice_extraction_alias_mapping() -> None:
    ext1 = InvoiceExtraction.model_validate({"vendor": "ACME", "invoice_number": "INV-2024-999"})
    assert ext1.receipt_number == "INV-2024-999"

    ext2 = InvoiceExtraction.model_validate({"vendor": "ACME", "rechnungsnummer": "RE-888"})
    assert ext2.receipt_number == "RE-888"

    ext3 = InvoiceExtraction.model_validate({"vendor": "ACME", "bill_no": "BILL-007"})
    assert ext3.receipt_number == "BILL-007"


def test_normalize_extraction_scales_resolves_power_of_ten_errors() -> None:
    # 16,0000 misparsed by VLM as 160000.0 with qty=4 and total=64.0
    ext = InvoiceExtraction(
        vendor="NormTest",
        receipt_number="INV-01",
        subtotal=64000.0,
        total_amount=64.0,
        line_items=[
            LineItemSchema(
                description="Bügelgriff Aluminium",
                quantity=4.0,
                unit_price=160000.0,
                total_price=64.0,
            )
        ],
    )
    normalized = normalize_extraction_scales(ext)
    assert normalized.line_items[0].unit_price == 16.0
    assert normalized.subtotal == 64.0
    assert normalized.total_amount == 64.0

    rec = reconcile_invoice(ext)
    assert rec.totals_reconcile is True
    assert rec.items_match_subtotal is True
    assert rec.needs_escalation is False
