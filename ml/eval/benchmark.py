"""Phase 1 benchmark runner comparing Baseline LayoutLMv3 vs Indra OCR + VLMs."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from eval.paths import QWEN35_08B_DIR, REPO_ROOT, XIAOMI_OCR_DIR, configure_local_caches

configure_local_caches(offline=True)

from eval.datasets import load_eval_suite  # noqa: E402
from eval.metrics import DatasetAggregate, score_prediction  # noqa: E402
from eval.runners import (  # noqa: E402
    BaselineLayoutLMv3Runner,
    IndraOCRFrontEnd,
    IndraVLMRunner,
    RunnerResult,
)
from eval.temp_manifest import EvalSample  # noqa: E402

AVAILABLE_CONFIGS: dict[str, dict[str, Any]] = {
    "baseline": {"kind": "baseline"},
    "xiaomi-bf16": {"kind": "vlm", "model_dir": XIAOMI_OCR_DIR, "precision": "bf16"},
    "xiaomi-fp16": {"kind": "vlm", "model_dir": XIAOMI_OCR_DIR, "precision": "fp16"},
    "xiaomi-4bit": {"kind": "vlm", "model_dir": XIAOMI_OCR_DIR, "precision": "4bit"},
    "qwen35-bf16": {"kind": "vlm", "model_dir": QWEN35_08B_DIR, "precision": "bf16"},
    "qwen35-fp16": {"kind": "vlm", "model_dir": QWEN35_08B_DIR, "precision": "fp16"},
    "qwen35-4bit": {"kind": "vlm", "model_dir": QWEN35_08B_DIR, "precision": "4bit"},
}


def build_ocr_cache(
    suites: dict[str, list[EvalSample]],
    indra: IndraOCRFrontEnd,
) -> dict[tuple[str, str], tuple[str, list[Any], float, str | None]]:
    """Precompute Indra OCR outputs once across all samples so VLM configs share OCR cleanly."""
    cache: dict[tuple[str, str], tuple[str, list[Any], float, str | None]] = {}
    t0 = time.perf_counter()
    total = sum(len(items) for items in suites.values())
    done = 0
    for ds_name, items in suites.items():
        for sample in items:
            done += 1
            try:
                ocr_text, imgs, lat = indra.read_sample(sample)
                cache[(ds_name, sample.sample_id)] = (ocr_text, imgs, lat, None)
            except Exception as exc:  # noqa: BLE001
                cache[(ds_name, sample.sample_id)] = ("", [], 0.0, f"{type(exc).__name__}: {exc}")
            if done % 20 == 0 or done == total:
                elapsed = time.perf_counter() - t0
                print(f"[Indra OCR cache] {done}/{total} ({elapsed:.1f}s)", flush=True)
    return cache


def _run_config(
    cfg_name: str,
    suites: dict[str, list[EvalSample]],
    ocr_cache: dict[tuple[str, str], tuple[str, list[Any], float, str | None]],
    indra: IndraOCRFrontEnd | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate one model config across all suites."""
    spec = AVAILABLE_CONFIGS[cfg_name]
    print(f"\n=== Running {cfg_name} ===", flush=True)
    if spec["kind"] == "baseline":
        runner: BaselineLayoutLMv3Runner | IndraVLMRunner = BaselineLayoutLMv3Runner()
    else:
        assert indra is not None
        runner = IndraVLMRunner(
            name=cfg_name,
            model_dir=spec["model_dir"],
            indra=indra,
            precision=spec["precision"],
        )

    summaries: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    try:
        for ds_name, samples in suites.items():
            agg = DatasetAggregate(model_name=cfg_name, dataset_name=ds_name)
            t_ds = time.perf_counter()
            for idx, sample in enumerate(samples, start=1):
                if isinstance(runner, BaselineLayoutLMv3Runner):
                    res = runner.run(sample)
                else:
                    ocr_text, imgs, ocr_lat, ocr_err = ocr_cache[(ds_name, sample.sample_id)]
                    if ocr_err:
                        res = RunnerResult(
                            prediction=None,
                            json_valid=False,
                            latency_s=ocr_lat,
                            ocr_latency_s=ocr_lat,
                            model_latency_s=0.0,
                            peak_vram_mb=0.0,
                            raw_output="",
                            error=ocr_err,
                        )
                    else:
                        res = runner.run_with_ocr(
                            sample,
                            ocr_text=ocr_text,
                            images=imgs,
                            ocr_latency_s=ocr_lat,
                        )

                detail = score_prediction(
                    agg,
                    res.prediction,
                    sample.ground_truth,
                    json_valid=res.json_valid,
                    latency_s=res.latency_s,
                    ocr_latency_s=res.ocr_latency_s,
                    vlm_latency_s=res.model_latency_s,
                    peak_vram_mb=res.peak_vram_mb,
                )
                records.append(
                    {
                        "model": cfg_name,
                        "dataset": ds_name,
                        "sample_id": sample.sample_id,
                        "is_multipage_stress": sample.is_multipage_stress,
                        "json_valid": res.json_valid,
                        "latency_s": round(res.latency_s, 3),
                        "ocr_latency_s": round(res.ocr_latency_s, 3),
                        "model_latency_s": round(res.model_latency_s, 3),
                        "peak_vram_mb": round(res.peak_vram_mb, 1),
                        "error": res.error,
                        "ground_truth": sample.ground_truth,
                        "prediction": res.prediction.model_dump() if res.prediction else None,
                        "raw_output": res.raw_output,
                        "scores": detail,
                    }
                )
                if idx % 10 == 0 or idx == len(samples):
                    print(
                        f"  [{cfg_name}][{ds_name}] {idx}/{len(samples)} "
                        f"({time.perf_counter() - t_ds:.1f}s)",
                        flush=True,
                    )

            summary = agg.summarize()
            summaries.append(summary)
            print(f"Summary [{cfg_name}][{ds_name}]: {json.dumps(summary)}", flush=True)
    finally:
        runner.close()

    return summaries, records


def _fmt_pct(val: float | None) -> str:
    return "-" if val is None else f"{val * 100:.1f}%"


def format_markdown_report(
    summaries: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> str:
    """Format benchmark metrics and key failure examples into a clean Markdown report."""
    lines = [
        "# Phase 1 Benchmark Report",
        "",
        "## Dataset Summary",
        "",
        "| Model | Dataset | N | JSON Valid | Mean (s) | Median (s) | Peak VRAM (MiB) | "
        "Vendor (Fuzzy) | Date (Exact) | Total (Close) | Line-Item F1 | Math Reconcile |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        flds = s["fields"]
        lines.append(
            "| "
            + " | ".join(
                [
                    s["model"],
                    s["dataset"],
                    str(s["n"]),
                    _fmt_pct(s["json_valid_rate"]),
                    f"{s['mean_latency_s']:.2f}",
                    f"{s['median_latency_s']:.2f}",
                    f"{s['peak_vram_mb']:.0f}",
                    _fmt_pct(flds.get("vendor_fuzzy")),
                    _fmt_pct(flds.get("date_exact")),
                    _fmt_pct(flds.get("total_amount_close")),
                    _fmt_pct(s.get("line_item_f1")),
                    _fmt_pct(s.get("math_reconcile_rate")),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Detailed Field Breakdown", ""])
    for s in summaries:
        lines.append(f"### {s['model']} — {s['dataset']}")
        lines.append(
            f"- Latency: mean `{s['mean_latency_s']:.2f}s`, median `{s['median_latency_s']:.2f}s` "
            f"(OCR `{s['mean_ocr_s']:.2f}s`, Model `{s['mean_vlm_s']:.2f}s`), "
            f"Peak VRAM `{s['peak_vram_mb']:.1f} MiB`"
        )
        field_parts = [f"`{k}`: {_fmt_pct(v)}" for k, v in s["fields"].items()]
        if s.get("line_item_recall") is not None:
            field_parts.append(f"`line_item_recall`: {_fmt_pct(s['line_item_recall'])}")
        if s.get("line_item_price_match") is not None:
            field_parts.append(f"`line_item_price_match`: {_fmt_pct(s['line_item_price_match'])}")
        if s.get("items_sum_match_rate") is not None:
            field_parts.append(f"`items_sum_match`: {_fmt_pct(s['items_sum_match_rate'])}")
        if field_parts:
            lines.append("- Metrics: " + ", ".join(field_parts))
        lines.append("")

    stress = [r for r in records if r["is_multipage_stress"]]
    if stress:
        lines.extend(["## Multi-Page PDF Stress (`sample-tables.pdf`)", ""])
        for r in stress:
            lines.append(
                f"- `{r['model']}`: json_valid=`{r['json_valid']}`, latency=`{r['latency_s']}s` "
                f"(OCR `{r['ocr_latency_s']}s`, VLM `{r['model_latency_s']}s`), "
                f"vram=`{r['peak_vram_mb']} MiB`, error=`{r['error']}`"
            )
        lines.append("")

    # Surface concrete total/JSON misses per model for LoRA gap analysis
    lines.extend(["## Sample Errors & Misses (Top 5 per Model)", ""])
    models_seen = list(dict.fromkeys(r["model"] for r in records))
    for m in models_seen:
        misses = []
        for r in records:
            if r["model"] != m or r["is_multipage_stress"]:
                continue
            tot_ok = r["scores"].get("total_amount", {}).get("close", True)
            if not r["json_valid"] or r["error"] or not tot_ok:
                misses.append(r)
        lines.append(f"### {m} ({len(misses)} JSON/total failures)")
        for r in misses[:5]:
            pred_tot = (r["prediction"] or {}).get("total_amount")
            gt_tot = r["ground_truth"].get("total_amount")
            lines.append(
                f"- `{r['dataset']}/{r['sample_id']}`: json_valid=`{r['json_valid']}`, "
                f"gt_total=`{gt_tot}`, pred_total=`{pred_tot}`, err=`{r['error']}`"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sroie-limit", type=int, default=40)
    parser.add_argument("--cord-limit", type=int, default=40)
    parser.add_argument("--cord-split", default="test")
    parser.add_argument(
        "--configs",
        nargs="+",
        default=["baseline", "xiaomi-bf16", "xiaomi-4bit", "qwen35-bf16", "qwen35-4bit"],
        choices=list(AVAILABLE_CONFIGS.keys()),
    )
    parser.add_argument("--smoke", action="store_true", help="Run tiny 7-doc smoke benchmark")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "ml" / "eval" / "results",
    )
    args = parser.parse_args()

    if args.smoke:
        suites = load_eval_suite(
            sroie_limit=2,
            cord_limit=2,
            cord_split=args.cord_split,
            include_temp=True,
        )
        smoke_ids = {
            "sample_pdf_2.pdf",
            "invoice-eur-english.png",
            "swc enterprise receipt.jpeg",
        }
        suites["temp_docs"] = [s for s in suites["temp_docs"] if s.sample_id in smoke_ids]
        prefix = "smoke_"
    else:
        suites = load_eval_suite(
            sroie_limit=args.sroie_limit,
            cord_limit=args.cord_limit,
            cord_split=args.cord_split,
            include_temp=True,
        )
        prefix = "benchmark_"

    print("Loaded datasets:", {k: len(v) for k, v in suites.items()}, flush=True)

    needs_indra = any(AVAILABLE_CONFIGS[c]["kind"] == "vlm" for c in args.configs)
    indra = IndraOCRFrontEnd() if needs_indra else None
    ocr_cache = build_ocr_cache(suites, indra) if indra is not None else {}

    all_summaries: list[dict[str, Any]] = []
    all_records: list[dict[str, Any]] = []
    for cfg in args.configs:
        s_list, r_list = _run_config(cfg, suites, ocr_cache, indra)
        all_summaries.extend(s_list)
        all_records.extend(r_list)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{prefix}results.json"
    md_path = args.output_dir / f"{prefix}report.md"

    json_path.write_text(
        json.dumps({"summaries": all_summaries, "records": all_records}, indent=2, default=str),
        encoding="utf-8",
    )
    report_md = format_markdown_report(all_summaries, all_records)
    md_path.write_text(report_md, encoding="utf-8")

    print(f"\nSaved JSON -> {json_path}")
    print(f"Saved Report -> {md_path}\n")
    print(report_md)


if __name__ == "__main__":
    main()
