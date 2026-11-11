"""Evaluation normalization and scoring metrics for SROIE, CORD-v2, and temp docs."""

from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass, field
from typing import Any

from dateutil import parser as date_parser
from rapidfuzz import fuzz

from eval.schemas import ExtractionValidation, InvoiceExtraction, parse_money


def norm_text(val: str | None) -> str:
    """Normalize text for exact/fuzzy comparison (lowercase, collapse spaces/punct)."""
    if not val:
        return ""
    s = str(val).lower().strip()
    s = re.sub(r"[\s]+", " ", s)
    return s


def norm_alnum(val: str | None) -> str:
    """Normalize text stripping non-alphanumeric punctuation except spaces."""
    if not val:
        return ""
    s = re.sub(r"[^a-z0-9\s]", " ", str(val).lower())
    return re.sub(r"\s+", " ", s).strip()


def norm_date(val: str | None) -> str:
    """Try normalizing a date string to ISO YYYY-MM-DD, fallback to norm_text."""
    if not val:
        return ""
    text = str(val).strip()
    # Clean common receipt noise
    cleaned = re.sub(r"\b(?:date|datum|tgl)\s*[:.]?\s*", "", text, flags=re.IGNORECASE).strip()
    # SROIE/German receipts are often DD/MM/YYYY or DD.MM.YYYY
    dayfirst = bool(re.match(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", cleaned))
    try:
        dt = date_parser.parse(cleaned, dayfirst=dayfirst, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return norm_text(cleaned)


def match_text_field(
    pred: str | None,
    gt: str | None,
    *,
    fuzzy_threshold: float = 85.0,
) -> dict[str, Any]:
    """Compare string fields returning exact, normalized exact, and token_set_ratio."""
    if not gt:
        return {"present": False}
    p_norm = norm_alnum(pred)
    g_norm = norm_alnum(gt)
    if not p_norm:
        return {"present": True, "exact": False, "fuzzy_match": False, "similarity": 0.0}
    exact = p_norm == g_norm
    sim = float(fuzz.token_set_ratio(p_norm, g_norm))
    if not exact:
        # SROIE OCR sometimes concatenates spaces or drops single chars
        ratio = float(fuzz.ratio(p_norm, g_norm))
        sim = max(sim, ratio)
    return {
        "present": True,
        "exact": exact,
        "fuzzy_match": exact or sim >= fuzzy_threshold,
        "similarity": sim,
    }


def match_date_field(pred: str | None, gt: str | None) -> dict[str, Any]:
    """Compare dates after ISO normalization, allowing exact numeric substring fallback."""
    if not gt:
        return {"present": False}
    if not pred:
        return {"present": True, "exact": False, "fuzzy_match": False, "similarity": 0.0}
    pn = norm_date(pred)
    gn = norm_date(gt)
    exact = pn == gn
    # Handle DD/MM vs MM/DD ambiguity on day <= 12
    alt_exact = False
    if not exact and len(pn) == 10 and len(gn) == 10 and pn[:4] == gn[:4]:
        if pn[5:7] == gn[8:10] and pn[8:10] == gn[5:7]:
            alt_exact = True
    sim = 100.0 if (exact or alt_exact) else float(fuzz.ratio(norm_alnum(pred), norm_alnum(gt)))
    return {
        "present": True,
        "exact": exact or alt_exact,
        "fuzzy_match": exact or alt_exact or sim >= 90.0,
        "similarity": sim,
    }


def match_amount_field(
    pred: float | str | None,
    gt: float | str | None,
    *,
    rel_tol: float = 0.015,
    abs_tol: float = 0.05,
) -> dict[str, Any]:
    """Compare numeric monetary amounts within relative/absolute tolerance."""
    g_num = gt if isinstance(gt, (int, float)) else parse_money(gt)
    if g_num is None:
        return {"present": False}
    p_num = pred if isinstance(pred, (int, float)) else parse_money(pred)
    if p_num is None or math.isnan(p_num):
        return {"present": True, "exact": False, "close": False}

    # Check exact rounded to 2 decimals or tight tolerance
    exact = abs(p_num - g_num) <= 1e-2
    tol = max(abs_tol, rel_tol * max(abs(g_num), 1.0))
    close = abs(p_num - g_num) <= tol
    return {"present": True, "exact": exact, "close": close, "abs_err": abs(p_num - g_num)}


def match_line_items(
    pred_items: list[Any],
    gt_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate line-item description recall/precision and price match via greedy matching."""
    if not gt_items:
        return {"present": False}

    p_list = [
        {
            "description": getattr(it, "description", None) or it.get("description", ""),
            "total_price": getattr(it, "total_price", None)
            if hasattr(it, "total_price")
            else it.get("total_price"),
            "quantity": getattr(it, "quantity", None)
            if hasattr(it, "quantity")
            else it.get("quantity"),
        }
        for it in (pred_items or [])
    ]

    if not p_list:
        return {
            "present": True,
            "gt_count": len(gt_items),
            "pred_count": 0,
            "desc_recall": 0.0,
            "desc_precision": 0.0,
            "desc_f1": 0.0,
            "price_match_rate": 0.0,
        }

    # Pair each GT item to best unused prediction by description similarity
    used_pred: set[int] = set()
    desc_matches = 0
    price_matches = 0
    price_total = 0

    for g in gt_items:
        g_desc = norm_alnum(g.get("description"))
        best_idx = -1
        best_sim = -1.0
        for idx, p in enumerate(p_list):
            if idx in used_pred:
                continue
            p_desc = norm_alnum(p.get("description"))
            if not p_desc or not g_desc:
                continue
            sim = float(fuzz.token_set_ratio(g_desc, p_desc))
            if sim > best_sim:
                best_sim = sim
                best_idx = idx
        if best_idx >= 0 and best_sim >= 70.0:
            used_pred.add(best_idx)
            desc_matches += 1
            g_price = parse_money(g.get("total_price"))
            if g_price is not None:
                price_total += 1
                p_price = p_list[best_idx].get("total_price")
                if p_price is not None and match_amount_field(p_price, g_price)["close"]:
                    price_matches += 1

    recall = desc_matches / len(gt_items)
    precision = desc_matches / len(p_list)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    price_rate = (price_matches / price_total) if price_total > 0 else None

    return {
        "present": True,
        "gt_count": len(gt_items),
        "pred_count": len(p_list),
        "desc_recall": recall,
        "desc_precision": precision,
        "desc_f1": f1,
        "price_match_rate": price_rate,
    }


@dataclass
class DatasetAggregate:
    """Aggregate benchmark metrics for a (model, dataset) pair."""

    model_name: str
    dataset_name: str
    num_samples: int = 0
    json_valid_count: int = 0
    latencies_s: list[float] = field(default_factory=list)
    ocr_latencies_s: list[float] = field(default_factory=list)
    vlm_latencies_s: list[float] = field(default_factory=list)
    peak_vram_mb: float = 0.0
    field_scores: dict[str, list[bool]] = field(default_factory=dict)
    line_item_f1s: list[float] = field(default_factory=list)
    line_item_recalls: list[float] = field(default_factory=list)
    line_item_price_rates: list[float] = field(default_factory=list)
    math_reconcile_checks: list[bool] = field(default_factory=list)
    items_match_checks: list[bool] = field(default_factory=list)

    def add_field(self, name: str, passed: bool) -> None:
        self.field_scores.setdefault(name, []).append(passed)

    def summarize(self) -> dict[str, Any]:
        """Compute summary rates and timing percentiles."""
        field_summary = {
            k: round(sum(v) / len(v), 4) for k, v in sorted(self.field_scores.items()) if v
        }
        return {
            "model": self.model_name,
            "dataset": self.dataset_name,
            "n": self.num_samples,
            "json_valid_rate": round(self.json_valid_count / max(self.num_samples, 1), 4),
            "mean_latency_s": round(statistics.mean(self.latencies_s), 3)
            if self.latencies_s
            else 0.0,
            "median_latency_s": round(statistics.median(self.latencies_s), 3)
            if self.latencies_s
            else 0.0,
            "mean_ocr_s": round(statistics.mean(self.ocr_latencies_s), 3)
            if self.ocr_latencies_s
            else 0.0,
            "mean_vlm_s": round(statistics.mean(self.vlm_latencies_s), 3)
            if self.vlm_latencies_s
            else 0.0,
            "peak_vram_mb": round(self.peak_vram_mb, 1),
            "fields": field_summary,
            "line_item_f1": round(statistics.mean(self.line_item_f1s), 4)
            if self.line_item_f1s
            else None,
            "line_item_recall": round(statistics.mean(self.line_item_recalls), 4)
            if self.line_item_recalls
            else None,
            "line_item_price_match": round(statistics.mean(self.line_item_price_rates), 4)
            if self.line_item_price_rates
            else None,
            "math_reconcile_rate": round(
                sum(self.math_reconcile_checks) / len(self.math_reconcile_checks), 4
            )
            if self.math_reconcile_checks
            else None,
            "items_sum_match_rate": round(
                sum(self.items_match_checks) / len(self.items_match_checks), 4
            )
            if self.items_match_checks
            else None,
        }


def score_prediction(
    agg: DatasetAggregate,
    pred: InvoiceExtraction | None,
    gt: dict[str, Any],
    *,
    json_valid: bool,
    latency_s: float,
    ocr_latency_s: float = 0.0,
    vlm_latency_s: float = 0.0,
    peak_vram_mb: float = 0.0,
) -> dict[str, Any]:
    """Score one prediction against ground truth and accumulate into ``agg``."""
    agg.num_samples += 1
    if json_valid:
        agg.json_valid_count += 1
    agg.latencies_s.append(latency_s)
    agg.ocr_latencies_s.append(ocr_latency_s)
    agg.vlm_latencies_s.append(vlm_latency_s)
    agg.peak_vram_mb = max(agg.peak_vram_mb, peak_vram_mb)

    sample_detail: dict[str, Any] = {}
    p = pred or InvoiceExtraction()

    if gt.get("vendor"):
        res = match_text_field(p.vendor, gt["vendor"])
        agg.add_field("vendor_fuzzy", res["fuzzy_match"])
        agg.add_field("vendor_exact", res["exact"])
        sample_detail["vendor"] = res

    if gt.get("vendor_address"):
        res = match_text_field(p.vendor_address, gt["vendor_address"], fuzzy_threshold=80.0)
        agg.add_field("address_fuzzy", res["fuzzy_match"])
        sample_detail["vendor_address"] = res

    if gt.get("date"):
        res = match_date_field(p.date, gt["date"])
        agg.add_field("date_exact", res["exact"])
        sample_detail["date"] = res

    if gt.get("receipt_number"):
        res = match_text_field(p.receipt_number, gt["receipt_number"], fuzzy_threshold=90.0)
        agg.add_field("receipt_no_exact", res["exact"])
        sample_detail["receipt_number"] = res

    if gt.get("currency"):
        cur_p = norm_text(p.currency)
        cur_g = norm_text(gt["currency"])
        matched = bool(cur_p and (cur_p == cur_g or cur_g in cur_p or cur_p in cur_g))
        agg.add_field("currency", matched)
        sample_detail["currency"] = matched

    for amt_key in ("subtotal", "tax_amount", "discount_amount", "total_amount"):
        if gt.get(amt_key) is not None:
            res = match_amount_field(getattr(p, amt_key), gt[amt_key])
            agg.add_field(f"{amt_key}_close", res["close"])
            sample_detail[amt_key] = res

    if gt.get("line_items"):
        li_res = match_line_items(p.line_items, gt["line_items"])
        agg.line_item_f1s.append(li_res["desc_f1"])
        agg.line_item_recalls.append(li_res["desc_recall"])
        if li_res["price_match_rate"] is not None:
            agg.line_item_price_rates.append(li_res["price_match_rate"])
        sample_detail["line_items"] = li_res

    if pred is not None:
        val = ExtractionValidation.check(pred)
        if val.totals_reconcile is not None:
            agg.math_reconcile_checks.append(val.totals_reconcile)
        if val.items_match_subtotal is not None:
            agg.items_match_checks.append(val.items_match_subtotal)
        sample_detail["validation"] = val.model_dump()

    return sample_detail
