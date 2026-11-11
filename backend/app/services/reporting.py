"""Bulk report generators (JSON, formula-safe CSV, XSS-escaped HTML)."""

from __future__ import annotations

import csv
import html
import io
import json
from typing import Any

from app.db.models import InvoiceRecord
from app.db.repository import record_to_detail, to_float

_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe_text(value: str | None) -> str:
    if not value:
        return ""
    if value[0] in _CSV_FORMULA_PREFIXES:
        return f"'{value}"
    return value


def _fmt_num(val: Any) -> str:
    num = to_float(val)
    if num is None:
        return ""
    return f"{num:.2f}"


def generate_json_report(records: list[InvoiceRecord]) -> str:
    """Serialize selected invoices with full details and line items to JSON."""
    payload = [record_to_detail(rec).model_dump(mode="json") for rec in records]
    return json.dumps({"count": len(payload), "invoices": payload}, indent=2)


def generate_csv_report(records: list[InvoiceRecord]) -> str:
    """Serialize selected invoices into UTF-8 CSV protected against formula injection."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "filename",
            "status",
            "document_type",
            "vendor",
            "receipt_number",
            "date",
            "due_date",
            "currency",
            "subtotal",
            "tax_amount",
            "discount_amount",
            "total_amount",
            "line_items_count",
            "items_match_subtotal",
            "totals_reconcile",
            "duplicate_of_id",
            "created_at",
        ]
    )
    for rec in records:
        writer.writerow(
            [
                str(rec.id),
                _csv_safe_text(rec.filename),
                rec.status,
                rec.document_type,
                _csv_safe_text(rec.vendor),
                _csv_safe_text(rec.receipt_number),
                rec.invoice_date.isoformat() if rec.invoice_date else "",
                rec.due_date.isoformat() if rec.due_date else "",
                rec.currency or "",
                _fmt_num(rec.subtotal),
                _fmt_num(rec.tax_amount),
                _fmt_num(rec.discount_amount),
                _fmt_num(rec.total_amount),
                len(rec.line_items),
                "" if rec.items_match_subtotal is None else str(rec.items_match_subtotal),
                "" if rec.totals_reconcile is None else str(rec.totals_reconcile),
                str(rec.duplicate_of_id) if rec.duplicate_of_id else "",
                rec.created_at.isoformat() if rec.created_at else "",
            ]
        )
    return buf.getvalue()


def generate_html_report(records: list[InvoiceRecord]) -> str:
    """Generate a clean print-ready HTML summary escaping all dynamic fields."""
    esc = html.escape
    sections: list[str] = []

    for rec in records:
        items_rows = "\n".join(
            f"<tr>"
            f"<td>{esc(li.description)}</td>"
            f"<td>{esc(_fmt_num(li.quantity))}</td>"
            f"<td>{esc(_fmt_num(li.unit_price))}</td>"
            f"<td>{esc(_fmt_num(li.total_price))}</td>"
            f"</tr>"
            for li in sorted(rec.line_items, key=lambda x: x.position)
        )
        inv_date = rec.invoice_date.isoformat() if rec.invoice_date else "-"
        ccy = rec.currency or ""
        sub_txt = _fmt_num(rec.subtotal) or "-"
        tax_txt = _fmt_num(rec.tax_amount) or "-"
        tot_txt = _fmt_num(rec.total_amount) or "-"
        sections.append(
            f"""
            <section class="invoice-card">
              <h2>{esc(rec.vendor or rec.filename)}</h2>
              <p class="meta">
                <strong>File:</strong> {esc(rec.filename)} |
                <strong>Receipt #:</strong> {esc(rec.receipt_number or "-")} |
                <strong>Date:</strong> {esc(inv_date)} |
                <strong>Status:</strong> <span class="badge">{esc(rec.status)}</span>
              </p>
              <p class="totals">
                <strong>Subtotal:</strong> {esc(ccy)} {esc(sub_txt)} |
                <strong>Tax:</strong> {esc(tax_txt)} |
                <strong>Total:</strong> {esc(ccy)} {esc(tot_txt)}
              </p>
              <table>
                <thead>
                  <tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr>
                </thead>
                <tbody>{items_rows or '<tr><td colspan="4">No line items</td></tr>'}</tbody>
              </table>
            </section>
            """.strip()
        )

    body_content = "\n".join(sections) if sections else "<p>No invoices matched filter.</p>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Invoice Batch Report ({len(records)})</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #111827; }}
    .invoice-card {{
      border: 1px solid #d1d5db; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.25rem;
    }}
    .badge {{
      background: #e5e7eb; border-radius: 4px; padding: 0.1rem 0.4rem; font-size: 0.85rem;
    }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 0.75rem; font-size: 0.9rem; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; text-align: left; padding: 0.4rem 0.5rem; }}
    th {{ background: #f9fafb; }}
  </style>
</head>
<body>
  <h1>Invoice Processing Report ({len(records)} documents)</h1>
  {body_content}
</body>
</html>
"""
