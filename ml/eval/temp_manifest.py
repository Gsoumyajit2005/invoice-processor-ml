"""Curated ground-truth manifest for out-of-domain stress documents in ./temp."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval.paths import REPO_ROOT


@dataclass(frozen=True)
class EvalSample:
    """Single benchmark sample across SROIE, CORD-v2, or ./temp."""

    dataset: str
    sample_id: str
    path: Path | None
    image: Any | None  # PIL.Image.Image when loaded directly from Hugging Face dataset
    ground_truth: dict[str, Any]
    is_multipage_stress: bool = False


TEMP_SPECS: list[dict[str, Any]] = [
    {
        "filename": "sample_pdf_2.pdf",
        "gt": {
            "vendor": "Unternehmen für Computerteile",
            "receipt_number": "AUFNR234953",
            "date": "2022-05-02",
            "currency": "EUR",
            "subtotal": 216.00,
            "tax_amount": 41.04,
            "total_amount": 257.04,
            "line_items": [
                {
                    "description": "LED-Monitore 12'",
                    "quantity": 4.0,
                    "unit_price": 16.0,
                    "total_price": 64.0,
                },
                {
                    "description": "USB-Maus",
                    "quantity": 2.0,
                    "unit_price": 16.0,
                    "total_price": 32.0,
                },
                {
                    "description": "mechanische Tastatur",
                    "quantity": 5.0,
                    "unit_price": 24.0,
                    "total_price": 120.0,
                },
            ],
        },
    },
    {
        "filename": "sample_pdf_3.pdf",
        "gt": {
            "vendor": "MiningEquip (Deutschland)",
            "receipt_number": "AUFNR34869",
            "date": "2025-05-28",
            "currency": "EUR",
            "subtotal": 1080.00,
            "tax_amount": 205.20,
            "total_amount": 1285.20,
            "line_items": [
                {
                    "description": "Bohrmaschine",
                    "quantity": 4.0,
                    "unit_price": 160.0,
                    "total_price": 640.0,
                },
                {
                    "description": "Bergmannshelm mit Fackeln",
                    "quantity": 2.0,
                    "unit_price": 160.0,
                    "total_price": 320.0,
                },
                {
                    "description": "Schaufeln",
                    "quantity": 5.0,
                    "unit_price": 24.0,
                    "total_price": 120.0,
                },
            ],
        },
    },
    {
        "filename": "sample_pdf_4.pdf",
        "gt": {
            "vendor": "MedEquip (Deutschland) GmbH",
            "receipt_number": "AUFNR123456",
            "date": "2022-05-02",
            "currency": "EUR",
            "subtotal": 216.00,
            "tax_amount": 41.04,
            "total_amount": 257.04,
            "line_items": [
                {
                    "description": "Schutzmaske Medium",
                    "quantity": 4.0,
                    "unit_price": 16.0,
                    "total_price": 64.0,
                },
                {
                    "description": "Disp Mask small CV",
                    "quantity": 2.0,
                    "unit_price": 16.0,
                    "total_price": 32.0,
                },
                {
                    "description": "Standard-Monitoring EKG Elektrode",
                    "quantity": 5.0,
                    "unit_price": 24.0,
                    "total_price": 120.0,
                },
            ],
        },
    },
    {
        "filename": "invoice-eur-english.png",
        "gt": {
            "vendor": "Sample Company Ltd",
            "receipt_number": "SRV-1895",
            "date": "2026-01-27",
            "currency": "EUR",
            "subtotal": 16310.00,
            "tax_amount": 3262.00,
            "total_amount": 19572.00,
            "line_items": [
                {
                    "description": "IT programming and consulting",
                    "quantity": 86.0,
                    "unit_price": 185.0,
                    "total_price": 15910.0,
                },
                {
                    "description": "Support hours",
                    "quantity": 4.0,
                    "unit_price": 70.0,
                    "total_price": 280.0,
                },
                {
                    "description": "Domain sample-company.net",
                    "quantity": 1.0,
                    "unit_price": 120.0,
                    "total_price": 120.0,
                },
            ],
        },
    },
    {
        "filename": "invoice-template-us-neat-750px.png",
        "gt": {
            "vendor": "East Repair Inc.",
            "receipt_number": "US-001",
            "date": "2019-02-11",
            "currency": "USD",
            "subtotal": 145.00,
            "tax_amount": 9.06,
            "total_amount": 154.06,
            "line_items": [
                {
                    "description": "Front and rear brake cables",
                    "quantity": 1.0,
                    "unit_price": 100.0,
                    "total_price": 100.0,
                },
                {
                    "description": "New set of pedal arms",
                    "quantity": 2.0,
                    "unit_price": 15.0,
                    "total_price": 30.0,
                },
                {
                    "description": "Labor 3hrs",
                    "quantity": 3.0,
                    "unit_price": 5.0,
                    "total_price": 15.0,
                },
            ],
        },
    },
    {
        "filename": "667045f840c501441620d236_Real-Estate-Invoice-Green.png",
        "gt": {
            "vendor": "Dreamwise Reality",
            "receipt_number": "111",
            "date": "2024-04-25",
            "subtotal": 610.00,
            "tax_amount": 0.0,
            "total_amount": 610.00,
            "line_items": [
                {
                    "description": "Transaction Coordination Fee",
                    "quantity": 1.0,
                    "unit_price": 500.0,
                    "total_price": 500.0,
                },
                {
                    "description": "Showing Fee",
                    "quantity": 1.0,
                    "unit_price": 50.0,
                    "total_price": 50.0,
                },
                {
                    "description": "Maintenance Coordination Fee",
                    "quantity": 1.0,
                    "unit_price": 60.0,
                    "total_price": 60.0,
                },
            ],
        },
    },
    {
        "filename": "Training-and-tutoring-1-564x804.jpg",
        "gt": {
            "vendor": "Skill Mentor",
            "receipt_number": "012345",
            "date": "2021-12-08",
            "currency": "USD",
            "subtotal": 1210.00,
            "total_amount": 1210.00,
            "line_items": [
                {
                    "description": "Coding Course",
                    "quantity": 1.0,
                    "unit_price": 180.0,
                    "total_price": 180.0,
                },
                {
                    "description": "English Language Course",
                    "quantity": 1.0,
                    "unit_price": 150.0,
                    "total_price": 150.0,
                },
                {
                    "description": "Writing Skills Workshop",
                    "quantity": 1.0,
                    "unit_price": 400.0,
                    "total_price": 400.0,
                },
                {
                    "description": "Online Private Tutoring",
                    "quantity": 6.0,
                    "unit_price": 80.0,
                    "total_price": 480.0,
                },
            ],
        },
    },
    {
        "filename": "invoice_1.png",
        "gt": {
            "receipt_number": "12345",
            "date": "2050-03-15",
            "currency": "USD",
            "total_amount": 325.00,
            "line_items": [
                {
                    "description": "Wireless Bluetooth Headphones",
                    "quantity": 2.0,
                    "unit_price": 50.0,
                    "total_price": 100.0,
                },
                {
                    "description": "Premium Software Subscription",
                    "quantity": 1.0,
                    "unit_price": 150.0,
                    "total_price": 150.0,
                },
                {
                    "description": "Portable Power Bank",
                    "quantity": 3.0,
                    "unit_price": 20.0,
                    "total_price": 60.0,
                },
                {
                    "description": "Express Shipping Fee",
                    "quantity": 1.0,
                    "unit_price": 15.0,
                    "total_price": 15.0,
                },
            ],
        },
    },
    {
        "filename": "invoice_2.jpg",
        "gt": {
            "vendor": "East Repair Inc.",
            "receipt_number": "US-001",
            "date": "2019-02-11",
            "currency": "USD",
            "subtotal": 145.00,
            "tax_amount": 9.06,
            "total_amount": 154.06,
            "line_items": [
                {
                    "description": "Front and rear brake cables",
                    "quantity": 1.0,
                    "unit_price": 100.0,
                    "total_price": 100.0,
                },
                {
                    "description": "New set of pedal arms",
                    "quantity": 2.0,
                    "unit_price": 15.0,
                    "total_price": 30.0,
                },
                {
                    "description": "Labor 3hrs",
                    "quantity": 3.0,
                    "unit_price": 5.0,
                    "total_price": 15.0,
                },
            ],
        },
    },
    {
        "filename": "starbucks receipt.jpeg",
        "gt": {
            "vendor": "STARBUCKS",
            "receipt_number": "664290",
            "date": "2014-12-07",
            "currency": "USD",
            "subtotal": 4.95,
            "total_amount": 4.95,
            "line_items": [
                {"description": "Vt Pep Mocha", "total_price": 4.95},
            ],
        },
    },
    {
        "filename": "swc enterprise receipt.jpeg",
        "gt": {
            "vendor": "SWC ENTERPRISE SDN BHD",
            "receipt_number": "0100080332",
            "date": "2018-01-08",
            "tax_amount": 0.45,
            "total_amount": 8.00,
            "line_items": [
                {
                    "description": "20X30 1KG",
                    "quantity": 1.0,
                    "unit_price": 8.0,
                    "total_price": 8.0,
                },
            ],
        },
    },
    {
        "filename": "sample-tables.pdf",
        "is_multipage_stress": True,
        "gt": {},
    },
]


def load_temp_samples() -> list[EvalSample]:
    """Load curated non-SROIE invoices and multi-page PDFs from data/samples (or legacy ./temp)."""
    samples_dir = REPO_ROOT / "data" / "samples"
    legacy_dir = REPO_ROOT / "temp"
    samples: list[EvalSample] = []
    for spec in TEMP_SPECS:
        file_path = samples_dir / spec["filename"]
        if not file_path.exists():
            file_path = legacy_dir / spec["filename"]
        if not file_path.exists():
            continue
        samples.append(
            EvalSample(
                dataset="temp_docs",
                sample_id=spec["filename"],
                path=file_path,
                image=None,
                ground_truth=spec["gt"],
                is_multipage_stress=bool(spec.get("is_multipage_stress", False)),
            )
        )
    return samples
