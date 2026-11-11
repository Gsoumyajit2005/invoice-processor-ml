"""Deterministic synthetic multi-layout B2B invoice generator for LoRA training."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from PIL import Image, ImageDraw, ImageFont

_GERMAN_VENDORS = [
    ("Nordlicht Elektronik GmbH", "Hafenstraße 42, 20459 Hamburg"),
    ("Bavaria Werkzeugbau AG", "Industriering 18, 80939 München"),
    ("RheinTech Lösungen GmbH", "Domplatz 7, 50667 Köln"),
    ("AlpenMed Versorgung GmbH", "Bahnhofsallee 91, 70173 Stuttgart"),
    ("SpreeCloud Software KG", "Friedrichstraße 112, 10117 Berlin"),
]

_ENGLISH_VENDORS = [
    ("Apex Timber & Hardware Ltd", "240 Oakwood Ave, Austin, TX 78701"),
    ("Thames Industrial Supply Co", "18 Bishopsgate, London EC2N 4BQ"),
    ("Cascadia Logistics Corp", "410 Pine St, Seattle, WA 98101"),
    ("Deccan Precision Systems Pvt Ltd", "42 MG Road, Bengaluru 560001"),
    ("Harborview Medical Partners", "88 Beacon St, Boston, MA 02108"),
]

_BUYERS = [
    "Klara Weber / Weber Handel OHG",
    "Delta Freight Services Inc",
    "Stadtwerke Bergheim GmbH",
    "Orion Retail Group LLC",
    "Mittelstand Praxiszentrum",
    "Pacific Crest Builders",
]

_ITEMS_DE = [
    ("Industriesensor Typ K", 120.0),
    ("Netzteil 24V Hutschiene", 45.5),
    ("Kabelbaum geschirmt 5m", 18.75),
    ("Wartungspaket Basis", 290.0),
    ("Alugehäuse eloxiert", 64.0),
    ("Montageservice vor Ort", 95.0),
]

_ITEMS_EN = [
    ("Stainless Flange Kit 40mm", 82.5),
    ("Server Rack Cooling Fan", 54.0),
    ("Annual Support Retainer", 420.0),
    ("Optical Barcode Scanner", 135.0),
    ("Heavy Duty Pallet Wrap", 28.5),
    ("On-site Calibration Hour", 110.0),
]


@dataclass(frozen=True)
class SyntheticSample:
    """Generated invoice image with verified OCR-free full-schema ground truth."""

    sample_id: str
    split: str
    image: Image.Image
    ground_truth: dict[str, Any]


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fmt_num(val: float, *, european: bool) -> str:
    us = f"{val:,.2f}"
    if not european:
        return us
    return us.replace(",", "_").replace(".", ",").replace("_", ".")


def generate_synthetic_invoices(
    *,
    num_train: int = 48,
    num_val: int = 8,
    seed: int = 42,
) -> tuple[list[SyntheticSample], list[SyntheticSample]]:
    """Render diverse German/English B2B invoices and credit notes with exact GT."""
    rng = random.Random(seed)
    f_title = _load_font(26, bold=True)
    f_bold = _load_font(15, bold=True)
    f_reg = _load_font(14, bold=False)

    all_train: list[SyntheticSample] = []
    all_val: list[SyntheticSample] = []
    total = num_train + num_val

    for idx in range(total):
        split = "train" if idx < num_train else "val"
        is_german = idx % 2 == 0
        layout = idx % 3  # Rotate seller/buyer geometry across 3 distinct templates
        is_credit_note = (idx % 9 == 8)

        vendor, v_addr = (
            rng.choice(_GERMAN_VENDORS) if is_german else rng.choice(_ENGLISH_VENDORS)
        )
        bill_to = rng.choice(_BUYERS)
        inv_date = date(2024, 1, 5) + timedelta(days=rng.randint(0, 650))
        due_date = inv_date + timedelta(days=rng.choice([14, 30, 45]))

        if is_german:
            currency = "EUR"
            ccy_sym = "€"
            tax_rate = rng.choice([0.19, 0.07, 0.0])
            receipt_no = f"RE-{inv_date.year}-{rng.randint(1000, 9999)}"
            date_str = inv_date.strftime("%d.%m.%Y")
            due_str = due_date.strftime("%d.%m.%Y")
            catalog = _ITEMS_DE
        else:
            currency, ccy_sym = rng.choice([("USD", "$"), ("GBP", "£"), ("INR", "₹")])
            tax_rate = rng.choice([0.08, 0.20, 0.18, 0.0])
            receipt_no = f"INV-{inv_date.year}-{rng.randint(100, 999)}"
            date_str = inv_date.strftime("%b %d, %Y") if idx % 4 == 1 else inv_date.isoformat()
            due_str = due_date.strftime("%b %d, %Y") if idx % 4 == 1 else due_date.isoformat()
            catalog = _ITEMS_EN

        chosen_items = rng.sample(catalog, k=rng.randint(2, 4))
        line_items: list[dict[str, Any]] = []
        subtotal = 0.0
        for desc, unit in chosen_items:
            qty = float(rng.randint(1, 6))
            tot_line = round(qty * unit, 2)
            subtotal += tot_line
            line_items.append(
                {
                    "description": desc,
                    "quantity": qty,
                    "unit_price": unit,
                    "total_price": tot_line,
                }
            )
        subtotal = round(subtotal, 2)
        disc = round(subtotal * 0.05, 2) if idx % 5 == 2 else None
        taxable = round(subtotal - (disc or 0.0), 2)
        tax_amt = round(taxable * tax_rate, 2) if tax_rate > 0 else 0.0
        total_amt = round(taxable + tax_amt, 2)

        # Render clean 900x1180 RGB invoice image
        img = Image.new("RGB", (900, 1180), color=(252, 253, 255))
        draw = ImageDraw.Draw(img)

        doc_heading = (
            ("GUTSCHRIFT" if is_german else "CREDIT NOTE")
            if is_credit_note
            else ("RECHNUNG" if is_german else "INVOICE")
        )
        accent = (28, 78, 128) if is_german else (24, 96, 72)
        draw.rectangle([(0, 0), (900, 18)], fill=accent)

        if layout == 0:
            # Seller top-left, Invoice meta top-right, Bill-To below seller
            draw.text((55, 45), vendor, fill=(15, 23, 42), font=f_title)
            draw.text((55, 82), v_addr, fill=(71, 85, 105), font=f_reg)
            draw.text((620, 48), doc_heading, fill=accent, font=f_title)
            bill_x, bill_y = 55, 145
            meta_x, meta_y = 560, 145
        elif layout == 1:
            # Centered seller letterhead, Buyer top-left, Meta top-right
            draw.text((220, 38), vendor, fill=(15, 23, 42), font=f_title)
            draw.text((220, 74), v_addr, fill=(71, 85, 105), font=f_reg)
            draw.line([(55, 108), (845, 108)], fill=(203, 213, 225), width=2)
            draw.text((55, 122), doc_heading, fill=accent, font=f_bold)
            bill_x, bill_y = 55, 155
            meta_x, meta_y = 550, 125
        else:
            # Buyer left, Seller top-right
            draw.text((55, 48), doc_heading, fill=accent, font=f_title)
            draw.text((480, 48), vendor, fill=(15, 23, 42), font=f_bold)
            draw.text((480, 74), v_addr, fill=(71, 85, 105), font=f_reg)
            bill_x, bill_y = 55, 145
            meta_x, meta_y = 480, 145

        bill_lbl = "Rechnung an:" if is_german else "Bill To:"
        draw.text((bill_x, bill_y), bill_lbl, fill=accent, font=f_bold)
        draw.text((bill_x, bill_y + 24), bill_to, fill=(15, 23, 42), font=f_reg)

        no_lbl = "Rechnungsnummer" if is_german else "Invoice No"
        dt_lbl = "Rechnungsdatum" if is_german else "Date"
        due_lbl = "Fälligkeitsdatum" if is_german else "Due Date"
        draw.text((meta_x, meta_y), f"{no_lbl}: {receipt_no}", fill=(15, 23, 42), font=f_reg)
        draw.text((meta_x, meta_y + 24), f"{dt_lbl}: {date_str}", fill=(15, 23, 42), font=f_reg)
        draw.text((meta_x, meta_y + 48), f"{due_lbl}: {due_str}", fill=(15, 23, 42), font=f_reg)

        # Table header
        y = 265
        draw.rectangle([(55, y), (845, y + 34)], fill=(238, 242, 247))
        headers = (
            ("Beschreibung", "Menge", "Einzelpreis", "Gesamt")
            if is_german
            else ("Description", "Qty", "Unit Price", "Amount")
        )
        draw.text((68, y + 8), headers[0], fill=(15, 23, 42), font=f_bold)
        draw.text((480, y + 8), headers[1], fill=(15, 23, 42), font=f_bold)
        draw.text((585, y + 8), headers[2], fill=(15, 23, 42), font=f_bold)
        draw.text((735, y + 8), headers[3], fill=(15, 23, 42), font=f_bold)
        y += 48

        for item in line_items:
            qty_s = f"{int(item['quantity'])}"
            unit_s = f"{_fmt_num(item['unit_price'], european=is_german)} {ccy_sym}"
            tot_s = f"{_fmt_num(item['total_price'], european=is_german)} {ccy_sym}"
            draw.text((68, y), item["description"], fill=(30, 41, 59), font=f_reg)
            draw.text((490, y), qty_s, fill=(30, 41, 59), font=f_reg)
            draw.text((585, y), unit_s, fill=(30, 41, 59), font=f_reg)
            draw.text((735, y), tot_s, fill=(30, 41, 59), font=f_reg)
            draw.line([(55, y + 26), (845, y + 26)], fill=(226, 232, 240), width=1)
            y += 40

        y += 30
        sub_lbl = "Zwischensumme" if is_german else "Subtotal"
        tax_lbl = f"MwSt ({int(tax_rate * 100)}%)" if is_german else f"Tax ({int(tax_rate * 100)}%)"
        disc_lbl = "Rabatt" if is_german else "Discount"
        tot_lbl = "Gesamtbetrag" if is_german else "Total Due"

        draw.text((540, y), f"{sub_lbl}:", fill=(51, 65, 85), font=f_reg)
        draw.text(
            (730, y),
            f"{_fmt_num(subtotal, european=is_german)} {ccy_sym}",
            fill=(15, 23, 42),
            font=f_reg,
        )
        y += 28
        if disc is not None:
            draw.text((540, y), f"{disc_lbl}:", fill=(51, 65, 85), font=f_reg)
            draw.text(
                (730, y),
                f"-{_fmt_num(disc, european=is_german)} {ccy_sym}",
                fill=(15, 23, 42),
                font=f_reg,
            )
            y += 28
        draw.text((540, y), f"{tax_lbl}:", fill=(51, 65, 85), font=f_reg)
        draw.text(
            (730, y),
            f"{_fmt_num(tax_amt, european=is_german)} {ccy_sym}",
            fill=(15, 23, 42),
            font=f_reg,
        )
        y += 34
        draw.line([(530, y - 6), (845, y - 6)], fill=accent, width=2)
        draw.text((540, y + 4), f"{tot_lbl}:", fill=accent, font=f_bold)
        draw.text(
            (730, y + 4),
            f"{_fmt_num(total_amt, european=is_german)} {ccy_sym}",
            fill=accent,
            font=f_bold,
        )

        gt = {
            "document_type": "credit_note" if is_credit_note else "invoice",
            "vendor": vendor,
            "vendor_address": v_addr,
            "receipt_number": receipt_no,
            "date": inv_date.isoformat(),
            "due_date": due_date.isoformat(),
            "currency": currency,
            "subtotal": subtotal,
            "tax_amount": tax_amt,
            "discount_amount": disc,
            "total_amount": total_amt,
            "bill_to": bill_to,
            "line_items": line_items,
        }
        rec = SyntheticSample(
            sample_id=f"synth_{split}_{idx:03d}",
            split=split,
            image=img,
            ground_truth=gt,
        )
        (all_train if split == "train" else all_val).append(rec)

    return all_train, all_val
