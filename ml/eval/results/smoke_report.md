# Phase 1 Benchmark Report

## Dataset Summary

| Model | Dataset | N | JSON Valid | Mean (s) | Median (s) | Peak VRAM (MiB) | Vendor (Fuzzy) | Date (Exact) | Total (Close) | Line-Item F1 | Math Reconcile |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| xiaomi-fp16 | sroie_test | 2 | 100.0% | 6.70 | 6.70 | 1890 | 100.0% | 100.0% | 100.0% | - | 100.0% |
| xiaomi-fp16 | cord_v2_test | 2 | 100.0% | 3.79 | 3.79 | 1932 | - | - | 50.0% | 100.0% | 50.0% |
| xiaomi-fp16 | temp_docs | 3 | 100.0% | 7.27 | 7.29 | 2022 | 66.7% | 100.0% | 33.3% | 88.9% | 33.3% |
| qwen35-fp16 | sroie_test | 2 | 100.0% | 5.76 | 5.76 | 1890 | 100.0% | 100.0% | 100.0% | - | 100.0% |
| qwen35-fp16 | cord_v2_test | 2 | 100.0% | 4.89 | 4.89 | 1932 | - | - | 50.0% | 83.3% | 100.0% |
| qwen35-fp16 | temp_docs | 3 | 100.0% | 7.28 | 7.51 | 2022 | 33.3% | 100.0% | 66.7% | 88.9% | 100.0% |

## Detailed Field Breakdown

### xiaomi-fp16 — sroie_test
- Latency: mean `6.70s`, median `6.70s` (OCR `0.14s`, Model `6.55s`), Peak VRAM `1889.5 MiB`
- Metrics: `address_fuzzy`: 100.0%, `date_exact`: 100.0%, `total_amount_close`: 100.0%, `vendor_exact`: 100.0%, `vendor_fuzzy`: 100.0%, `items_sum_match`: 50.0%

### xiaomi-fp16 — cord_v2_test
- Latency: mean `3.79s`, median `3.79s` (OCR `0.12s`, Model `3.67s`), Peak VRAM `1932.3 MiB`
- Metrics: `discount_amount_close`: 0.0%, `subtotal_close`: 50.0%, `tax_amount_close`: 50.0%, `total_amount_close`: 50.0%, `line_item_recall`: 100.0%, `line_item_price_match`: 50.0%, `items_sum_match`: 100.0%

### xiaomi-fp16 — temp_docs
- Latency: mean `7.27s`, median `7.29s` (OCR `0.23s`, Model `7.04s`), Peak VRAM `2022.2 MiB`
- Metrics: `currency`: 100.0%, `date_exact`: 100.0%, `receipt_no_exact`: 33.3%, `subtotal_close`: 100.0%, `tax_amount_close`: 100.0%, `total_amount_close`: 33.3%, `vendor_exact`: 66.7%, `vendor_fuzzy`: 66.7%, `line_item_recall`: 100.0%, `line_item_price_match`: 77.8%, `items_sum_match`: 33.3%

### qwen35-fp16 — sroie_test
- Latency: mean `5.76s`, median `5.76s` (OCR `0.14s`, Model `5.62s`), Peak VRAM `1889.5 MiB`
- Metrics: `address_fuzzy`: 100.0%, `date_exact`: 100.0%, `total_amount_close`: 100.0%, `vendor_exact`: 100.0%, `vendor_fuzzy`: 100.0%, `items_sum_match`: 50.0%

### qwen35-fp16 — cord_v2_test
- Latency: mean `4.89s`, median `4.89s` (OCR `0.12s`, Model `4.77s`), Peak VRAM `1932.3 MiB`
- Metrics: `discount_amount_close`: 0.0%, `subtotal_close`: 100.0%, `tax_amount_close`: 100.0%, `total_amount_close`: 50.0%, `line_item_recall`: 100.0%, `line_item_price_match`: 100.0%, `items_sum_match`: 50.0%

### qwen35-fp16 — temp_docs
- Latency: mean `7.28s`, median `7.51s` (OCR `0.23s`, Model `7.05s`), Peak VRAM `2022.2 MiB`
- Metrics: `currency`: 100.0%, `date_exact`: 100.0%, `receipt_no_exact`: 66.7%, `subtotal_close`: 100.0%, `tax_amount_close`: 100.0%, `total_amount_close`: 66.7%, `vendor_exact`: 33.3%, `vendor_fuzzy`: 33.3%, `line_item_recall`: 100.0%, `line_item_price_match`: 100.0%, `items_sum_match`: 66.7%

## Sample Errors & Misses (Top 5 per Model)

### xiaomi-fp16 (3 JSON/total failures)
- `cord_v2_test/cord_test_000`: json_valid=`True`, gt_total=`60000.0`, pred_total=`60.0`, err=`None`
- `temp_docs/sample_pdf_2.pdf`: json_valid=`True`, gt_total=`257.04`, pred_total=`216.0`, err=`None`
- `temp_docs/swc enterprise receipt.jpeg`: json_valid=`True`, gt_total=`8.0`, pred_total=`10.45`, err=`None`

### qwen35-fp16 (2 JSON/total failures)
- `cord_v2_test/cord_test_000`: json_valid=`True`, gt_total=`60000.0`, pred_total=`65455.0`, err=`None`
- `temp_docs/swc enterprise receipt.jpeg`: json_valid=`True`, gt_total=`8.0`, pred_total=`8.45`, err=`None`
