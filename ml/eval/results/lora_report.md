# Phase 1 Benchmark Report

## Dataset Summary

| Model | Dataset | N | JSON Valid | Mean (s) | Median (s) | Peak VRAM (MiB) | Vendor (Fuzzy) | Date (Exact) | Total (Close) | Line-Item F1 | Math Reconcile |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen35-fp16 | sroie_test | 30 | 100.0% | 7.84 | 6.86 | 2048 | 83.3% | 83.3% | 70.0% | - | 50.0% |
| qwen35-fp16 | cord_v2_test | 30 | 96.7% | 5.60 | 4.97 | 1999 | - | - | 79.3% | 81.8% | 51.7% |
| qwen35-fp16 | temp_docs | 12 | 100.0% | 6.87 | 7.30 | 2766 | 40.0% | 100.0% | 90.9% | 94.7% | 90.9% |
| qwen35-lora-fp16 | sroie_test | 30 | 100.0% | 11.34 | 10.20 | 2082 | 100.0% | 96.7% | 86.7% | - | 50.0% |
| qwen35-lora-fp16 | cord_v2_test | 30 | 100.0% | 7.73 | 7.14 | 2035 | - | - | 100.0% | 96.0% | 76.7% |
| qwen35-lora-fp16 | temp_docs | 12 | 100.0% | 10.50 | 10.93 | 2801 | 70.0% | 100.0% | 100.0% | 97.0% | 100.0% |

## Detailed Field Breakdown

### qwen35-fp16 — sroie_test
- Latency: mean `7.84s`, median `6.86s` (OCR `0.15s`, Model `7.69s`), Peak VRAM `2048.2 MiB`
- Metrics: `address_fuzzy`: 80.0%, `date_exact`: 83.3%, `total_amount_close`: 70.0%, `vendor_exact`: 70.0%, `vendor_fuzzy`: 83.3%, `items_sum_match`: 58.6%

### qwen35-fp16 — cord_v2_test
- Latency: mean `5.60s`, median `4.97s` (OCR `0.09s`, Model `5.51s`), Peak VRAM `1999.0 MiB`
- Metrics: `discount_amount_close`: 0.0%, `subtotal_close`: 87.0%, `tax_amount_close`: 40.0%, `total_amount_close`: 79.3%, `line_item_recall`: 91.0%, `line_item_price_match`: 82.8%, `items_sum_match`: 65.5%

### qwen35-fp16 — temp_docs
- Latency: mean `6.87s`, median `7.30s` (OCR `0.20s`, Model `6.67s`), Peak VRAM `2765.6 MiB`
- Metrics: `currency`: 77.8%, `date_exact`: 100.0%, `receipt_no_exact`: 63.6%, `subtotal_close`: 88.9%, `tax_amount_close`: 100.0%, `total_amount_close`: 90.9%, `vendor_exact`: 40.0%, `vendor_fuzzy`: 40.0%, `line_item_recall`: 97.7%, `line_item_price_match`: 81.8%, `items_sum_match`: 63.6%

### qwen35-lora-fp16 — sroie_test
- Latency: mean `11.34s`, median `10.20s` (OCR `0.15s`, Model `11.19s`), Peak VRAM `2081.9 MiB`
- Metrics: `address_fuzzy`: 100.0%, `date_exact`: 96.7%, `total_amount_close`: 86.7%, `vendor_exact`: 83.3%, `vendor_fuzzy`: 100.0%, `items_sum_match`: 60.0%

### qwen35-lora-fp16 — cord_v2_test
- Latency: mean `7.73s`, median `7.14s` (OCR `0.09s`, Model `7.65s`), Peak VRAM `2034.9 MiB`
- Metrics: `discount_amount_close`: 0.0%, `subtotal_close`: 91.3%, `tax_amount_close`: 100.0%, `total_amount_close`: 100.0%, `line_item_recall`: 96.0%, `line_item_price_match`: 96.2%, `items_sum_match`: 90.0%

### qwen35-lora-fp16 — temp_docs
- Latency: mean `10.50s`, median `10.93s` (OCR `0.20s`, Model `10.30s`), Peak VRAM `2800.6 MiB`
- Metrics: `currency`: 100.0%, `date_exact`: 100.0%, `receipt_no_exact`: 63.6%, `subtotal_close`: 100.0%, `tax_amount_close`: 87.5%, `total_amount_close`: 100.0%, `vendor_exact`: 60.0%, `vendor_fuzzy`: 70.0%, `line_item_recall`: 100.0%, `line_item_price_match`: 72.7%, `items_sum_match`: 63.6%

## Multi-Page PDF Stress (`sample-tables.pdf`)

- `qwen35-fp16`: json_valid=`True`, latency=`5.245s` (OCR `0.803s`, VLM `4.442s`), vram=`2765.6 MiB`, error=`None`
- `qwen35-lora-fp16`: json_valid=`True`, latency=`6.734s` (OCR `0.803s`, VLM `5.931s`), vram=`2800.6 MiB`, error=`None`

## Sample Errors & Misses (Top 5 per Model)

### qwen35-fp16 (16 JSON/total failures)
- `sroie_test/X51005663300`: json_valid=`True`, gt_total=`7.0`, pred_total=`7.4`, err=`None`
- `sroie_test/X51006329183`: json_valid=`True`, gt_total=`27.0`, pred_total=`2700.0`, err=`None`
- `sroie_test/X51006555833`: json_valid=`True`, gt_total=`1.52`, pred_total=`14.12`, err=`None`
- `sroie_test/X51006556808`: json_valid=`True`, gt_total=`79.26`, pred_total=`60.34`, err=`None`
- `sroie_test/X51006619506`: json_valid=`True`, gt_total=`23.55`, pred_total=`25.55`, err=`None`

### qwen35-lora-fp16 (4 JSON/total failures)
- `sroie_test/X51006556808`: json_valid=`True`, gt_total=`79.26`, pred_total=`60.34`, err=`None`
- `sroie_test/X51006557169`: json_valid=`True`, gt_total=`5.0`, pred_total=`6.11`, err=`None`
- `sroie_test/X51006619506`: json_valid=`True`, gt_total=`23.55`, pred_total=`24.1`, err=`None`
- `sroie_test/X51006619760`: json_valid=`True`, gt_total=`29.1`, pred_total=`27.46`, err=`None`
