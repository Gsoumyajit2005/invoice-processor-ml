"""Curated evaluation dataset loaders for SROIE test, CORD-v2 test, and ./temp docs."""

from __future__ import annotations

import json
import pickle
import re
from pathlib import Path
from typing import Any

from eval.paths import REPO_ROOT, configure_local_caches
from eval.schemas import clean_optional_str, parse_money
from eval.temp_manifest import EvalSample, load_temp_samples

configure_local_caches(offline=True)

from datasets import load_dataset  # noqa: E402


def parse_cord_money(value: Any) -> float | None:
    """Parse Indonesian Rupiah strings in CORD-v2 where '.' and ',' separate thousands."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    # Remove IDR / Rp / currency noise, keep digits, ',', '.', '-'
    negative = text.startswith("-")
    cleaned = re.sub(r"[^0-9.,]", "", text)
    if not cleaned:
        return None
    # In CORD-v2, both '60.000' and '24,000' denote integer IDR thousands.
    if re.fullmatch(r"\d+(?:[.,]\d{3})+", cleaned):
        num = float(re.sub(r"[.,]", "", cleaned))
    else:
        num = parse_money(cleaned)
        if num is None:
            return None
    return -abs(num) if negative else num


def _bio_tags_to_sroie_gt(words: list[str], labels: list[str]) -> dict[str, str]:
    """Reconstruct {company, date, address, total} strings from BIO token tags."""
    entities: dict[str, list[str]] = {}
    current_type: str | None = None
    current_tokens: list[str] = []

    def flush() -> None:
        nonlocal current_type, current_tokens
        if current_type and current_tokens:
            entities.setdefault(current_type, []).append(" ".join(current_tokens))
        current_type = None
        current_tokens = []

    for word, label in zip(words, labels, strict=True):
        if label.startswith("B-"):
            flush()
            current_type = label[2:].lower()
            current_tokens = [word]
        elif label.startswith("I-") and current_type == label[2:].lower():
            current_tokens.append(word)
        else:
            flush()
    flush()

    return {key: " ".join(vals) for key, vals in entities.items()}


def load_sroie_samples(limit: int = 40) -> list[EvalSample]:
    """Load a deterministic evenly-spaced subset of data/sroie/test receipts."""
    cache_pkl = REPO_ROOT / "data" / "doctr_trained_cache.pkl"
    gt_by_stem: dict[str, dict[str, Any]] = {}

    if cache_pkl.exists():
        with cache_pkl.open("rb") as fh:
            cached = pickle.load(fh)
        for rec in cached.get("test", []):
            stem = Path(rec["image_path"]).stem
            gt_by_stem[stem] = rec.get("ground_truth", {})

    images_dir = REPO_ROOT / "data" / "sroie" / "test" / "images"
    tagged_dir = REPO_ROOT / "data" / "sroie" / "test" / "tagged"
    all_images = sorted(images_dir.glob("*.jpg"))
    if not all_images:
        return []

    if limit and limit < len(all_images):
        step = len(all_images) / limit
        chosen = [all_images[int(i * step)] for i in range(limit)]
    else:
        chosen = all_images

    samples: list[EvalSample] = []
    for img_path in chosen:
        stem = img_path.stem
        raw_gt = dict(gt_by_stem.get(stem, {}))
        if not raw_gt:
            tag_file = tagged_dir / f"{stem}.json"
            if tag_file.exists():
                payload = json.loads(tag_file.read_text(encoding="utf-8"))
                raw_gt = _bio_tags_to_sroie_gt(payload["words"], payload["labels"])

        gt = {
            "vendor": clean_optional_str(raw_gt.get("company")),
            "vendor_address": clean_optional_str(raw_gt.get("address")),
            "date": clean_optional_str(raw_gt.get("date")),
            "total_amount": parse_money(raw_gt.get("total")),
        }
        # Skip degenerate empty records if any exist
        if not any(v is not None for v in gt.values()):
            continue
        samples.append(
            EvalSample(
                dataset="sroie_test",
                sample_id=stem,
                path=img_path,
                image=None,
                ground_truth=gt,
            )
        )
    return samples


def _extract_cord_line_items(menu_obj: Any) -> list[dict[str, Any]]:
    """Convert CORD-v2 ``menu`` dict or list into canonical line items."""
    if not menu_obj:
        return []
    entries = [menu_obj] if isinstance(menu_obj, dict) else list(menu_obj)
    items: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("nm")
        if isinstance(name, list):
            name = " ".join(str(x) for x in name if x)
        desc = clean_optional_str(name)
        price_val = parse_cord_money(entry.get("price") or entry.get("itemsubtotal"))
        qty_raw = entry.get("cnt")
        qty_val = parse_money(re.sub(r"[^0-9.,]", "", str(qty_raw))) if qty_raw else None
        unit_val = parse_cord_money(entry.get("unitprice"))

        # Include nested modifiers/sub-items when present
        sub = entry.get("sub")
        sub_list = [sub] if isinstance(sub, dict) else (sub if isinstance(sub, list) else [])
        sub_extra = 0.0
        for s in sub_list:
            if isinstance(s, dict) and s.get("price") is not None:
                sv = parse_cord_money(s.get("price"))
                if sv is not None:
                    sub_extra += sv

        if desc:
            items.append(
                {
                    "description": desc,
                    "quantity": qty_val,
                    "unit_price": unit_val,
                    "total_price": (price_val + sub_extra)
                    if (
                        price_val is not None
                        and sub_extra
                        and not items_already_include(price_val, sub_extra)
                    )
                    else price_val,
                }
            )
    return items


def items_already_include(main_price: float, sub_extra: float) -> bool:
    """Heuristic guard: CORD sub price is additive unless already rolled into main price."""
    return False if sub_extra > 0 and main_price >= 0 else True


def load_cord_samples(split: str = "test", limit: int = 40) -> list[EvalSample]:
    """Load curated deterministic subset from local cached naver-clova-ix/cord-v2."""
    ds = load_dataset("naver-clova-ix/cord-v2", split=split)
    n_total = len(ds)
    if limit and limit < n_total:
        step = n_total / limit
        indices = [int(i * step) for i in range(limit)]
    else:
        indices = list(range(n_total))

    samples: list[EvalSample] = []
    for idx in indices:
        row = ds[idx]
        parsed = json.loads(row["ground_truth"]).get("gt_parse", {})
        sub_total = parsed.get("sub_total", {}) or {}
        total_blk = parsed.get("total", {}) or {}

        subtotal_val = parse_cord_money(sub_total.get("subtotal_price"))
        tax_val = parse_cord_money(sub_total.get("tax_price"))
        disc_val = parse_cord_money(sub_total.get("discount_price"))
        if disc_val is not None:
            disc_val = abs(disc_val)
        total_val = parse_cord_money(total_blk.get("total_price"))
        line_items = _extract_cord_line_items(parsed.get("menu"))

        gt: dict[str, Any] = {}
        if subtotal_val is not None:
            gt["subtotal"] = subtotal_val
        if tax_val is not None:
            gt["tax_amount"] = tax_val
        if disc_val is not None:
            gt["discount_amount"] = disc_val
        if total_val is not None:
            gt["total_amount"] = total_val
        if line_items:
            gt["line_items"] = line_items

        samples.append(
            EvalSample(
                dataset=f"cord_v2_{split}",
                sample_id=f"cord_{split}_{idx:03d}",
                path=None,
                image=row["image"].convert("RGB"),
                ground_truth=gt,
            )
        )
    return samples


def load_eval_suite(
    *,
    sroie_limit: int = 40,
    cord_limit: int = 40,
    cord_split: str = "test",
    include_temp: bool = True,
) -> dict[str, list[EvalSample]]:
    """Load all three evaluation suites."""
    suites: dict[str, list[EvalSample]] = {}
    if sroie_limit > 0:
        suites["sroie_test"] = load_sroie_samples(limit=sroie_limit)
    if cord_limit > 0:
        suites[f"cord_v2_{cord_split}"] = load_cord_samples(split=cord_split, limit=cord_limit)
    if include_temp:
        suites["temp_docs"] = load_temp_samples()
    return suites
