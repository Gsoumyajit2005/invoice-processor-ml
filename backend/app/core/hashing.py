"""File byte hashing and null-safe semantic duplicate hashing."""

from __future__ import annotations

import hashlib
import re

from app.core.schemas import InvoiceExtraction


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hex digest of raw uploaded document bytes."""
    return hashlib.sha256(content).hexdigest()


def _norm_token(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def compute_semantic_hash(data: InvoiceExtraction) -> str | None:
    """Compute SHA-256 over normalized (vendor, receipt_number, date, total_amount).

    Returns None when fewer than 2 identifying fields are populated so empty/failed
    extractions never produce false-positive semantic duplicates.
    """
    vendor = _norm_token(data.vendor)
    receipt_no = _norm_token(data.receipt_number)
    inv_date = (data.date or "").strip()
    total = f"{data.total_amount:.2f}" if data.total_amount is not None else ""

    populated = sum(bool(x) for x in (vendor, receipt_no, inv_date, total))
    if populated < 2:
        return None
    if total and populated == 2 and not (vendor or receipt_no):
        return None

    canonical = "|".join((vendor, receipt_no, inv_date, total))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
