"""Prepare leak-free, schema-verified JSONL splits for Qwen3.5-0.8B LoRA training."""

from __future__ import annotations

import argparse
import gc
import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.paths import CACHE_DIR, QWEN35_08B_DIR, REPO_ROOT, configure_local_caches

configure_local_caches(offline=True)

from app.core.schemas import (  # noqa: E402
    InvoiceExtraction,
    clean_optional_str,
    normalize_currency,
    normalize_date,
    parse_money,
)
from dateutil import parser as date_parser  # noqa: E402
from eval.datasets import _bio_tags_to_sroie_gt, load_cord_samples  # noqa: E402
from eval.runners import IndraOCRFrontEnd, IndraVLMRunner, release_cuda  # noqa: E402
from eval.temp_manifest import EvalSample  # noqa: E402
from PIL import Image  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402

from train.synthetic_invoices import generate_synthetic_invoices  # noqa: E402

TRAIN_CACHE_DIR = REPO_ROOT / "ml" / "train" / "cache"
IMAGES_CACHE_DIR = TRAIN_CACHE_DIR / "images"
OCR_CACHE_PATH = TRAIN_CACHE_DIR / "ocr_cache.json"
TEACHER_CACHE_PATH = TRAIN_CACHE_DIR / "teacher_cache.json"

_MYR_RE = re.compile(r"\b(?:RM|MYR|SDN\.?\s*BHD|GST|SST|JALAN|JLN)\b", re.IGNORECASE)
_IDR_RE = re.compile(
    r"(?:\b(?:RP\.?|IDR|PB1|PPN|TUNAI|KEMBALI|TERIMA\s+KASIH)\b|\b\d{1,3}(?:\.\d{3})+\b)",
    re.IGNORECASE,
)
_USD_RE = re.compile(r"(?:\bUSD\b|US\$|\$\s*\d)", re.IGNORECASE)
_DATE_LIKE_OCR_RE = re.compile(
    r"(?:\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b|"
    r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{2,4}\b)",
    re.IGNORECASE,
)
_BOILERPLATE_VENDORS = {"RECEIPT", "INVOICE", "TAX INVOICE", "TOTAL", "BILL", "CASH", "SUBTOTAL"}


def _round_num(val: float | None, decimals: int = 2) -> float | None:
    if val is None:
        return None
    return round(float(val), decimals)


def _normalize_sroie_date(raw: Any) -> str | None:
    text = clean_optional_str(raw)
    if text is None:
        return None
    try:
        return normalize_date(text)
    except ValueError:
        pass
    try:
        return date_parser.parse(text, dayfirst=True, fuzzy=True).date().isoformat()
    except Exception:  # noqa: BLE001
        return None


def _load_sroie_train_samples(limit: int, *, seed: int) -> list[EvalSample]:
    """Load deterministically sampled receipts strictly from data/sroie/train/."""
    sroie_train_dir = REPO_ROOT / "data" / "sroie" / "train"
    tagged_files = sorted((sroie_train_dir / "tagged").glob("*.json"))
    candidates: list[EvalSample] = []

    for json_path in tagged_files:
        img_path = sroie_train_dir / "images" / f"{json_path.stem}.jpg"
        if not img_path.exists():
            continue
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        words: list[str] = payload.get("words", [])
        labels: list[str] = payload.get("labels", [])
        gt_raw = _bio_tags_to_sroie_gt(words, labels)
        total_val = parse_money(gt_raw.get("total"), strict=False)
        company = clean_optional_str(gt_raw.get("company"))
        if not company or total_val is None or total_val <= 0:
            continue
        candidates.append(
            EvalSample(
                dataset="sroie_train",
                sample_id=f"sroie_train_{json_path.stem}",
                path=img_path,
                image=None,
                ground_truth={
                    "vendor": company,
                    "vendor_address": clean_optional_str(gt_raw.get("address")),
                    "date": _normalize_sroie_date(gt_raw.get("date")),
                    "total_amount": float(total_val),
                },
            )
        )

    rng = random.Random(seed)
    rng.shuffle(candidates)
    return candidates[:limit]


def _load_json_dict(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_json_dict(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_ocr_and_image_cache(samples: list[EvalSample]) -> dict[str, dict[str, Any]]:
    """Run Indra OCR 1.1 once for uncached training/validation samples and persist PNGs."""
    IMAGES_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ocr_cache = _load_json_dict(OCR_CACHE_PATH)
    missing = [
        s
        for s in samples
        if s.sample_id not in ocr_cache
        or not (REPO_ROOT / ocr_cache[s.sample_id]["image_path"]).exists()
    ]
    if not missing:
        print(f"[prepare] OCR cache hit for all {len(samples)} samples.")
        return ocr_cache

    print(f"[prepare] Running Indra OCR 1.1 on {len(missing)} uncached samples...")
    indra = IndraOCRFrontEnd(threads=4, dpi=150.0)
    try:
        for idx, sample in enumerate(missing, start=1):
            ocr_text, images, ocr_lat = indra.read_sample(sample, max_vlm_pages=1)
            img = images[0] if images else Image.new("RGB", (640, 800), (255, 255, 255))
            img_path = IMAGES_CACHE_DIR / f"{sample.sample_id}.png"
            img.convert("RGB").save(img_path, format="PNG")
            ocr_cache[sample.sample_id] = {
                "image_path": str(img_path.relative_to(REPO_ROOT)),
                "ocr_text": ocr_text,
                "ocr_latency_s": round(ocr_lat, 3),
            }
            if idx % 25 == 0 or idx == len(missing):
                _save_json_dict(OCR_CACHE_PATH, ocr_cache)
                print(f"  [ocr] {idx}/{len(missing)} cached")
    finally:
        del indra
        gc.collect()
        release_cuda()

    return ocr_cache


def _run_teacher_completion(
    samples: list[EvalSample],
    ocr_cache: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Run frozen Qwen3.5-0.8B once to complete unannotated fields on SROIE/CORD."""
    teacher_cache = _load_json_dict(TEACHER_CACHE_PATH)
    missing = [s for s in samples if s.sample_id not in teacher_cache]
    if not missing:
        print(f"[prepare] Teacher cache hit for all {len(samples)} real samples.")
        return teacher_cache

    print(f"[prepare] Running frozen Qwen3.5-0.8B teacher on {len(missing)} samples...")
    runner = IndraVLMRunner(
        name="teacher-qwen35-fp16",
        model_dir=QWEN35_08B_DIR,
        indra=IndraOCRFrontEnd(threads=4, dpi=150.0),
        precision="fp16",
        use_ocr_context=True,
        max_new_tokens=1536,
        adapter_dir=None,
    )
    try:
        for idx, sample in enumerate(missing, start=1):
            rec = ocr_cache[sample.sample_id]
            img_path = REPO_ROOT / rec["image_path"]
            with Image.open(img_path) as im:
                rgb_img = im.convert("RGB")
            res = runner.run_with_ocr(
                sample,
                ocr_text=rec["ocr_text"],
                images=[rgb_img],
                ocr_latency_s=float(rec.get("ocr_latency_s", 0.0)),
            )
            teacher_cache[sample.sample_id] = {
                "json_valid": res.json_valid,
                "prediction": res.prediction.model_dump(
                    exclude={"provenance", "validation_warnings"}
                )
                if res.prediction is not None
                else None,
                "error": res.error,
            }
            if idx % 20 == 0 or idx == len(missing):
                _save_json_dict(TEACHER_CACHE_PATH, teacher_cache)
                print(f"  [teacher] {idx}/{len(missing)} cached")
    finally:
        runner.close()
        release_cuda()

    return teacher_cache


def _safe_teacher_model(entry: dict[str, Any] | None) -> InvoiceExtraction | None:
    if not entry or not entry.get("prediction"):
        return None
    try:
        return InvoiceExtraction.model_validate(entry["prediction"])
    except Exception:  # noqa: BLE001
        return None


def _currency_supported_by_ocr(ccy: str | None, ocr_text: str) -> bool:
    if not ccy:
        return False
    upper = ocr_text.upper()
    if ccy == "MYR":
        return bool(_MYR_RE.search(ocr_text))
    if ccy == "IDR":
        return bool(_IDR_RE.search(ocr_text))
    if ccy == "USD":
        return bool(_USD_RE.search(ocr_text))
    return ccy in upper


def _infer_sroie_currency(ocr_text: str, teacher: InvoiceExtraction | None) -> str | None:
    if _MYR_RE.search(ocr_text):
        return "MYR"
    if teacher and teacher.currency and _currency_supported_by_ocr(teacher.currency, ocr_text):
        return normalize_currency(teacher.currency)
    # SROIE corpus consists of Malaysian receipts priced in MYR.
    return "MYR"


def _infer_cord_currency(ocr_text: str, teacher: InvoiceExtraction | None) -> str | None:
    # Guard against MYR hallucination unless explicitly present in OCR text.
    if _MYR_RE.search(ocr_text):
        return "MYR"
    if _IDR_RE.search(ocr_text):
        return "IDR"
    if _USD_RE.search(ocr_text):
        return "USD"
    if teacher and teacher.currency and _currency_supported_by_ocr(teacher.currency, ocr_text):
        return normalize_currency(teacher.currency)
    return None


def _sanitize_line_items(items: list[Any], *, max_sum: float | None) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    running = 0.0
    for it in items:
        desc = clean_optional_str(
            getattr(it, "description", None) if not isinstance(it, dict) else it.get("description")
        )
        if not desc:
            continue
        qty = getattr(it, "quantity", None) if not isinstance(it, dict) else it.get("quantity")
        unit = getattr(it, "unit_price", None) if not isinstance(it, dict) else it.get("unit_price")
        tot = (
            getattr(it, "total_price", None) if not isinstance(it, dict) else it.get("total_price")
        )
        if tot is not None and tot < 0:
            continue
        if tot is not None:
            running += float(tot)
        cleaned.append(
            {
                "description": desc,
                "quantity": _round_num(qty, 3),
                "unit_price": _round_num(unit, 2),
                "total_price": _round_num(tot, 2),
            }
        )
    if max_sum is not None and cleaned and running > max(max_sum * 1.10, max_sum + 2.0):
        return []
    return cleaned


def _clean_sroie_receipt_number(rn: str | None, ocr_text: str) -> str | None:
    val = clean_optional_str(rn)
    if not val:
        return None
    # Prevent copying company GST / SSM registration IDs as receipt_number.
    if re.search(
        rf"(?:gst|reg\.?|ssm|co\.?\s*reg)\s*(?:id|no\.?)?\s*[:#]?\s*{re.escape(val)}",
        ocr_text,
        re.IGNORECASE,
    ):
        return None
    return val


def _clean_cord_vendor(
    vendor: str | None, ocr_text: str, gt_items: list[dict[str, Any]]
) -> str | None:
    val = clean_optional_str(vendor)
    if not val or len(val) < 2 or val.upper() in _BOILERPLATE_VENDORS:
        return None
    # Reject product codes or menu descriptions echoed into vendor on cropped CORD receipts.
    if re.fullmatch(r"[\d\s\-./]+", val):
        return None
    for it in gt_items:
        desc = clean_optional_str(it.get("description"))
        if desc and fuzz.token_set_ratio(val.lower(), desc.lower()) >= 70.0:
            return None
    header_zone = ocr_text.split("<table>", 1)[0]
    if fuzz.partial_ratio(val.upper(), header_zone.upper()) < 75.0:
        return None
    return val


def _clean_cord_date(raw_date: str | None, ocr_text: str) -> str | None:
    iso = _normalize_sroie_date(raw_date)
    if not iso or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso):
        return None
    year_int = int(iso[:4])
    # CORD-v2 receipts predate 2021; reject boilerplate 2024/2025 hallucinations & non-date SKUs.
    if year_int < 2010 or year_int > 2020:
        return None
    if not _DATE_LIKE_OCR_RE.search(ocr_text):
        return None
    yy = iso[2:4]
    if iso[:4] not in ocr_text and yy not in ocr_text:
        return None
    return iso


def _clean_cord_receipt_number(
    rn: str | None, ocr_text: str, gt_items: list[dict[str, Any]]
) -> str | None:
    val = clean_optional_str(rn)
    if not val or len(val) < 3:
        return None
    for it in gt_items:
        desc = clean_optional_str(it.get("description"))
        if desc and val.lower() in desc.lower():
            return None
    if not re.search(
        rf"(?:rec(?:eipt)?|inv(?:oice)?|bill|no\.?|#|trx|order)\s*[:#]?\s*{re.escape(val)}",
        ocr_text,
        re.IGNORECASE,
    ):
        return None
    return val


def _assemble_sroie_target(
    gt: dict[str, Any],
    ocr_text: str,
    teacher: InvoiceExtraction | None,
) -> dict[str, Any]:
    gt_total = float(gt["total_amount"])
    tol = max(0.05, 0.02 * gt_total)
    subtotal: float | None = None
    tax_amount: float | None = None
    discount_amount: float | None = None
    line_items: list[dict[str, Any]] = []

    if teacher is not None:
        line_items = _sanitize_line_items(teacher.line_items, max_sum=gt_total)
        t_sub = teacher.subtotal
        t_tax = teacher.tax_amount
        t_disc = teacher.discount_amount
        t_tot = teacher.total_amount

        total_ok = t_tot is not None and abs(t_tot - gt_total) <= tol
        disc_ok = t_disc is None or (0.0 <= t_disc <= gt_total * 0.50)
        tax_ok = t_tax is None or (0.0 <= t_tax <= gt_total * 0.25)

        if total_ok and disc_ok and tax_ok:
            disc_v = t_disc or 0.0
            tax_v = t_tax or 0.0
            if t_sub is None:
                subtotal = None
                tax_amount = _round_num(t_tax, 2)
                discount_amount = _round_num(t_disc, 2)
            elif abs((t_sub + tax_v - disc_v) - gt_total) <= tol:
                subtotal = _round_num(t_sub, 2)
                tax_amount = _round_num(t_tax, 2)
                discount_amount = _round_num(t_disc, 2)
            elif 0.0 < tax_v <= gt_total * 0.16 and abs((t_sub - disc_v) - gt_total) <= tol:
                # Valid tax-inclusive receipt (e.g. Malaysian GST 6% where subtotal == total)
                subtotal = _round_num(t_sub, 2)
                tax_amount = _round_num(t_tax, 2)
                discount_amount = _round_num(t_disc, 2)
        elif disc_ok and t_tax is not None and 0.0 < t_tax <= gt_total * 0.16:
            # Recover inclusive-GST failure where teacher set subtotal == gt_total and added tax
            if t_sub is None or abs(t_sub - gt_total) <= tol:
                subtotal = _round_num(gt_total, 2)
                tax_amount = _round_num(t_tax, 2)
                discount_amount = _round_num(t_disc, 2)

    bill_to = teacher.bill_to if teacher else None
    if bill_to and clean_optional_str(gt.get("vendor")) == bill_to:
        bill_to = None

    receipt_no = (
        _clean_sroie_receipt_number(teacher.receipt_number, ocr_text) if teacher else None
    )

    return {
        "document_type": "receipt",
        "vendor": clean_optional_str(gt.get("vendor")),
        "vendor_address": clean_optional_str(gt.get("vendor_address")),
        "receipt_number": receipt_no,
        "date": gt.get("date"),
        "due_date": None,
        "currency": _infer_sroie_currency(ocr_text, teacher),
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
        "total_amount": _round_num(gt_total, 2),
        "bill_to": bill_to,
        "line_items": line_items,
    }


def _assemble_cord_target(
    gt: dict[str, Any],
    ocr_text: str,
    teacher: InvoiceExtraction | None,
) -> dict[str, Any]:
    gt_items = _sanitize_line_items(gt.get("line_items") or [], max_sum=None)
    t_vendor = _clean_cord_vendor(teacher.vendor, ocr_text, gt_items) if teacher else None
    t_date = _clean_cord_date(teacher.date, ocr_text) if teacher else None
    t_rn = (
        _clean_cord_receipt_number(teacher.receipt_number, ocr_text, gt_items)
        if teacher
        else None
    )
    return {
        "document_type": "receipt",
        "vendor": t_vendor,
        "vendor_address": None,
        "receipt_number": t_rn,
        "date": t_date,
        "due_date": None,
        "currency": _infer_cord_currency(ocr_text, teacher),
        "subtotal": _round_num(gt.get("subtotal"), 2),
        "tax_amount": _round_num(gt.get("tax_amount"), 2),
        "discount_amount": _round_num(gt.get("discount_amount"), 2),
        "total_amount": _round_num(gt.get("total_amount"), 2),
        "bill_to": None,
        "line_items": gt_items,
    }


def prepare_splits(args: argparse.Namespace) -> dict[str, Any]:
    """Build deterministic leak-free train and validation JSONL datasets."""
    sroie_all = _load_sroie_train_samples(args.sroie_train + args.sroie_val, seed=args.seed)
    sroie_train = sroie_all[: args.sroie_train]
    sroie_val = sroie_all[args.sroie_train : args.sroie_train + args.sroie_val]

    cord_train = load_cord_samples(split="train", limit=args.cord_train)
    cord_val = load_cord_samples(split="validation", limit=args.cord_val)

    synth_train_raw, synth_val_raw = generate_synthetic_invoices(
        num_train=args.synth_train,
        num_val=args.synth_val,
        seed=args.seed,
    )
    synth_train = [
        EvalSample(
            dataset="synthetic_train",
            sample_id=s.sample_id,
            path=None,
            image=s.image,
            ground_truth=s.ground_truth,
        )
        for s in synth_train_raw
    ]
    synth_val = [
        EvalSample(
            dataset="synthetic_val",
            sample_id=s.sample_id,
            path=None,
            image=s.image,
            ground_truth=s.ground_truth,
        )
        for s in synth_val_raw
    ]

    all_train = sroie_train + cord_train + synth_train
    all_val = sroie_val + cord_val + synth_val
    ocr_cache = _build_ocr_and_image_cache(all_train + all_val)

    real_samples = sroie_train + sroie_val + cord_train + cord_val
    teacher_cache = _run_teacher_completion(real_samples, ocr_cache)

    records_by_split: dict[str, list[dict[str, Any]]] = {"train": [], "val": []}
    source_counts: Counter[str] = Counter()
    invalid_skipped = 0

    for split_name, split_samples in [("train", all_train), ("val", all_val)]:
        for sample in split_samples:
            ocr_entry = ocr_cache[sample.sample_id]
            ocr_text: str = ocr_entry["ocr_text"]
            teacher = _safe_teacher_model(teacher_cache.get(sample.sample_id))

            if sample.dataset.startswith("sroie"):
                target = _assemble_sroie_target(sample.ground_truth, ocr_text, teacher)
                source = "sroie_train"
            elif sample.dataset.startswith("cord"):
                target = _assemble_cord_target(sample.ground_truth, ocr_text, teacher)
                source = "cord_train"
            else:
                target = sample.ground_truth
                source = "synthetic"

            try:
                validated = InvoiceExtraction.model_validate(target)
                canonical_dict = validated.model_dump(
                    exclude={"provenance", "validation_warnings"}
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] skipping invalid sample {sample.sample_id}: {exc}")
                invalid_skipped += 1
                continue

            records_by_split[split_name].append(
                {
                    "sample_id": sample.sample_id,
                    "source": source,
                    "split": split_name,
                    "image_path": ocr_entry["image_path"],
                    "ocr_text": ocr_text,
                    "target_json": json.dumps(canonical_dict, ensure_ascii=False),
                }
            )
            source_counts[f"{split_name}:{source}"] += 1

    rng = random.Random(args.seed)
    rng.shuffle(records_by_split["train"])

    for split_name, recs in records_by_split.items():
        out_path = TRAIN_CACHE_DIR / f"{split_name}.jsonl"
        out_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
            encoding="utf-8",
        )

    summary = {
        "cache_dir": str(CACHE_DIR),
        "train_count": len(records_by_split["train"]),
        "val_count": len(records_by_split["val"]),
        "invalid_skipped": invalid_skipped,
        "source_breakdown": dict(sorted(source_counts.items())),
    }
    _save_json_dict(TRAIN_CACHE_DIR / "prep_summary.json", summary)
    print(f"[prepare] Done: {json.dumps(summary, indent=2)}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare LoRA training splits in ml/train/cache/")
    parser.add_argument("--sroie-train", type=int, default=120)
    parser.add_argument("--sroie-val", type=int, default=16)
    parser.add_argument("--cord-train", type=int, default=100)
    parser.add_argument("--cord-val", type=int, default=16)
    parser.add_argument("--synth-train", type=int, default=48)
    parser.add_argument("--synth-val", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    prepare_splits(args)


if __name__ == "__main__":
    main()
