# Phase 1 Benchmark Report

## Dataset Summary

| Model | Dataset | N | JSON Valid | Mean (s) | Median (s) | Peak VRAM (MiB) | Vendor (Fuzzy) | Date (Exact) | Total (Close) | Line-Item F1 | Math Reconcile |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | sroie_test | 30 | 100.0% | 0.38 | 0.31 | 1035 | 93.3% | 93.3% | 80.0% | - | 10.0% |
| baseline | cord_v2_test | 30 | 100.0% | 0.22 | 0.21 | 1007 | - | - | 48.3% | 61.1% | 23.8% |
| baseline | temp_docs | 12 | 100.0% | 0.34 | 0.32 | 1036 | 60.0% | 72.7% | 36.4% | 46.7% | 12.5% |
| xiaomi-fp16 | sroie_test | 30 | 96.7% | 8.14 | 7.83 | 2028 | 93.3% | 93.3% | 86.7% | - | 44.8% |
| xiaomi-fp16 | cord_v2_test | 30 | 100.0% | 5.70 | 5.08 | 1983 | - | - | 58.6% | 82.6% | 51.7% |
| xiaomi-fp16 | temp_docs | 12 | 100.0% | 7.76 | 7.52 | 2758 | 70.0% | 100.0% | 72.7% | 93.9% | 63.6% |
| xiaomi-4bit | sroie_test | 30 | 56.7% | 10.40 | 9.26 | 1162 | 56.7% | 53.3% | 46.7% | - | 52.9% |
| xiaomi-4bit | cord_v2_test | 30 | 66.7% | 7.56 | 6.22 | 1120 | - | - | 37.9% | 44.4% | 68.4% |
| xiaomi-4bit | temp_docs | 12 | 83.3% | 8.43 | 8.28 | 1895 | 50.0% | 72.7% | 54.5% | 78.8% | 55.6% |
| qwen35-fp16 | sroie_test | 30 | 96.7% | 7.96 | 7.07 | 2028 | 96.7% | 73.3% | 63.3% | - | 41.4% |
| qwen35-fp16 | cord_v2_test | 30 | 100.0% | 5.85 | 5.09 | 1983 | - | - | 82.8% | 84.9% | 66.7% |
| qwen35-fp16 | temp_docs | 12 | 100.0% | 7.07 | 7.39 | 2758 | 70.0% | 100.0% | 90.9% | 91.7% | 100.0% |
| qwen35-4bit | sroie_test | 30 | 96.7% | 9.49 | 8.82 | 1162 | 90.0% | 83.3% | 76.7% | - | 51.7% |
| qwen35-4bit | cord_v2_test | 30 | 96.7% | 6.89 | 5.82 | 1120 | - | - | 65.5% | 77.9% | 66.7% |
| qwen35-4bit | temp_docs | 12 | 100.0% | 8.54 | 8.85 | 1895 | 50.0% | 90.9% | 72.7% | 90.9% | 90.9% |

## Detailed Field Breakdown

### baseline — sroie_test
- Latency: mean `0.38s`, median `0.31s` (OCR `0.24s`, Model `0.12s`), Peak VRAM `1035.4 MiB`
- Metrics: `address_fuzzy`: 100.0%, `date_exact`: 93.3%, `total_amount_close`: 80.0%, `vendor_exact`: 80.0%, `vendor_fuzzy`: 93.3%, `items_sum_match`: 10.0%

### baseline — cord_v2_test
- Latency: mean `0.22s`, median `0.21s` (OCR `0.13s`, Model `0.09s`), Peak VRAM `1006.8 MiB`
- Metrics: `discount_amount_close`: 0.0%, `subtotal_close`: 0.0%, `tax_amount_close`: 0.0%, `total_amount_close`: 48.3%, `line_item_recall`: 69.6%, `line_item_price_match`: 50.0%, `items_sum_match`: 23.8%

### baseline — temp_docs
- Latency: mean `0.34s`, median `0.32s` (OCR `0.23s`, Model `0.10s`), Peak VRAM `1036.0 MiB`
- Metrics: `currency`: 0.0%, `date_exact`: 72.7%, `receipt_no_exact`: 54.5%, `subtotal_close`: 0.0%, `tax_amount_close`: 0.0%, `total_amount_close`: 36.4%, `vendor_exact`: 50.0%, `vendor_fuzzy`: 60.0%, `line_item_recall`: 54.5%, `line_item_price_match`: 85.7%, `items_sum_match`: 12.5%

### xiaomi-fp16 — sroie_test
- Latency: mean `8.14s`, median `7.83s` (OCR `0.16s`, Model `7.98s`), Peak VRAM `2028.0 MiB`
- Metrics: `address_fuzzy`: 90.0%, `date_exact`: 93.3%, `total_amount_close`: 86.7%, `vendor_exact`: 66.7%, `vendor_fuzzy`: 93.3%, `items_sum_match`: 53.6%

### xiaomi-fp16 — cord_v2_test
- Latency: mean `5.70s`, median `5.08s` (OCR `0.09s`, Model `5.61s`), Peak VRAM `1983.1 MiB`
- Metrics: `discount_amount_close`: 0.0%, `subtotal_close`: 69.6%, `tax_amount_close`: 60.0%, `total_amount_close`: 58.6%, `line_item_recall`: 91.0%, `line_item_price_match`: 65.5%, `items_sum_match`: 75.0%

### xiaomi-fp16 — temp_docs
- Latency: mean `7.76s`, median `7.52s` (OCR `0.21s`, Model `7.55s`), Peak VRAM `2758.1 MiB`
- Metrics: `currency`: 55.6%, `date_exact`: 100.0%, `receipt_no_exact`: 63.6%, `subtotal_close`: 100.0%, `tax_amount_close`: 100.0%, `total_amount_close`: 72.7%, `vendor_exact`: 60.0%, `vendor_fuzzy`: 70.0%, `line_item_recall`: 100.0%, `line_item_price_match`: 93.9%, `items_sum_match`: 72.7%

### xiaomi-4bit — sroie_test
- Latency: mean `10.40s`, median `9.26s` (OCR `0.16s`, Model `10.24s`), Peak VRAM `1161.9 MiB`
- Metrics: `address_fuzzy`: 56.7%, `date_exact`: 53.3%, `total_amount_close`: 46.7%, `vendor_exact`: 36.7%, `vendor_fuzzy`: 56.7%, `items_sum_match`: 66.7%

### xiaomi-4bit — cord_v2_test
- Latency: mean `7.56s`, median `6.22s` (OCR `0.09s`, Model `7.47s`), Peak VRAM `1119.5 MiB`
- Metrics: `discount_amount_close`: 0.0%, `subtotal_close`: 47.8%, `tax_amount_close`: 46.7%, `total_amount_close`: 37.9%, `line_item_recall`: 53.3%, `line_item_price_match`: 35.0%, `items_sum_match`: 64.7%

### xiaomi-4bit — temp_docs
- Latency: mean `8.43s`, median `8.28s` (OCR `0.21s`, Model `8.22s`), Peak VRAM `1894.7 MiB`
- Metrics: `currency`: 44.4%, `date_exact`: 72.7%, `receipt_no_exact`: 63.6%, `subtotal_close`: 77.8%, `tax_amount_close`: 87.5%, `total_amount_close`: 54.5%, `vendor_exact`: 50.0%, `vendor_fuzzy`: 50.0%, `line_item_recall`: 81.8%, `line_item_price_match`: 81.8%, `items_sum_match`: 88.9%

### qwen35-fp16 — sroie_test
- Latency: mean `7.96s`, median `7.07s` (OCR `0.16s`, Model `7.80s`), Peak VRAM `2028.0 MiB`
- Metrics: `address_fuzzy`: 96.7%, `date_exact`: 73.3%, `total_amount_close`: 63.3%, `vendor_exact`: 73.3%, `vendor_fuzzy`: 96.7%, `items_sum_match`: 64.3%

### qwen35-fp16 — cord_v2_test
- Latency: mean `5.85s`, median `5.09s` (OCR `0.09s`, Model `5.75s`), Peak VRAM `1983.1 MiB`
- Metrics: `discount_amount_close`: 0.0%, `subtotal_close`: 91.3%, `tax_amount_close`: 80.0%, `total_amount_close`: 82.8%, `line_item_recall`: 97.3%, `line_item_price_match`: 90.2%, `items_sum_match`: 70.0%

### qwen35-fp16 — temp_docs
- Latency: mean `7.07s`, median `7.39s` (OCR `0.21s`, Model `6.86s`), Peak VRAM `2758.1 MiB`
- Metrics: `currency`: 100.0%, `date_exact`: 100.0%, `receipt_no_exact`: 81.8%, `subtotal_close`: 100.0%, `tax_amount_close`: 100.0%, `total_amount_close`: 90.9%, `vendor_exact`: 70.0%, `vendor_fuzzy`: 70.0%, `line_item_recall`: 97.7%, `line_item_price_match`: 100.0%, `items_sum_match`: 81.8%

### qwen35-4bit — sroie_test
- Latency: mean `9.49s`, median `8.82s` (OCR `0.16s`, Model `9.33s`), Peak VRAM `1161.9 MiB`
- Metrics: `address_fuzzy`: 86.7%, `date_exact`: 83.3%, `total_amount_close`: 76.7%, `vendor_exact`: 66.7%, `vendor_fuzzy`: 90.0%, `items_sum_match`: 61.5%

### qwen35-4bit — cord_v2_test
- Latency: mean `6.89s`, median `5.82s` (OCR `0.09s`, Model `6.80s`), Peak VRAM `1119.5 MiB`
- Metrics: `discount_amount_close`: 0.0%, `subtotal_close`: 56.5%, `tax_amount_close`: 46.7%, `total_amount_close`: 65.5%, `line_item_recall`: 84.8%, `line_item_price_match`: 65.5%, `items_sum_match`: 65.4%

### qwen35-4bit — temp_docs
- Latency: mean `8.54s`, median `8.85s` (OCR `0.21s`, Model `8.33s`), Peak VRAM `1894.7 MiB`
- Metrics: `currency`: 88.9%, `date_exact`: 90.9%, `receipt_no_exact`: 63.6%, `subtotal_close`: 77.8%, `tax_amount_close`: 87.5%, `total_amount_close`: 72.7%, `vendor_exact`: 50.0%, `vendor_fuzzy`: 50.0%, `line_item_recall`: 97.7%, `line_item_price_match`: 87.9%, `items_sum_match`: 72.7%

## Multi-Page PDF Stress (`sample-tables.pdf`)

- `baseline`: json_valid=`True`, latency=`0.331s` (OCR `0.229s`, VLM `0.093s`), vram=`1032.4 MiB`, error=`None`
- `xiaomi-fp16`: json_valid=`True`, latency=`14.078s` (OCR `0.848s`, VLM `13.229s`), vram=`2758.1 MiB`, error=`None`
- `xiaomi-4bit`: json_valid=`True`, latency=`6.425s` (OCR `0.848s`, VLM `5.577s`), vram=`1894.7 MiB`, error=`None`
- `qwen35-fp16`: json_valid=`True`, latency=`5.146s` (OCR `0.848s`, VLM `4.298s`), vram=`2758.1 MiB`, error=`None`
- `qwen35-4bit`: json_valid=`True`, latency=`5.634s` (OCR `0.848s`, VLM `4.785s`), vram=`1894.7 MiB`, error=`None`

## Sample Errors & Misses (Top 5 per Model)

### baseline (28 JSON/total failures)
- `sroie_test/X51005710963`: json_valid=`True`, gt_total=`7.4`, pred_total=`7.0`, err=`None`
- `sroie_test/X51006329183`: json_valid=`True`, gt_total=`27.0`, pred_total=`27227.0`, err=`None`
- `sroie_test/X51006557169`: json_valid=`True`, gt_total=`5.0`, pred_total=`5765.0`, err=`None`
- `sroie_test/X51006619506`: json_valid=`True`, gt_total=`23.55`, pred_total=`0.85`, err=`None`
- `sroie_test/X51007103687`: json_valid=`True`, gt_total=`1.9`, pred_total=`1901.9`, err=`None`

### xiaomi-fp16 (19 JSON/total failures)
- `sroie_test/X51006414702`: json_valid=`True`, gt_total=`157.9`, pred_total=`167.2`, err=`None`
- `sroie_test/X51006619506`: json_valid=`True`, gt_total=`23.55`, pred_total=`26.0`, err=`None`
- `sroie_test/X51006912959`: json_valid=`False`, gt_total=`10.9`, pred_total=`None`, err=`json_decode_error: Expecting property name enclosed in double quotes: line 24 column 5 (char 595)`
- `sroie_test/X51007103687`: json_valid=`True`, gt_total=`1.9`, pred_total=`4.01`, err=`None`
- `cord_v2_test/cord_test_000`: json_valid=`True`, gt_total=`60000.0`, pred_total=`60.0`, err=`None`

### xiaomi-4bit (40 JSON/total failures)
- `sroie_test/X51005288570`: json_valid=`True`, gt_total=`1.0`, pred_total=`0.94`, err=`None`
- `sroie_test/X51005433556`: json_valid=`False`, gt_total=`49.7`, pred_total=`None`, err=`no_json_object_found`
- `sroie_test/X51005719888`: json_valid=`False`, gt_total=`39.8`, pred_total=`None`, err=`json_decode_error: Expecting property name enclosed in double quotes: line 18 column 5 (char 442)`
- `sroie_test/X51005746210`: json_valid=`False`, gt_total=`145.1`, pred_total=`None`, err=`no_json_object_found`
- `sroie_test/X51005764161`: json_valid=`False`, gt_total=`98.9`, pred_total=`None`, err=`no_json_object_found`

### qwen35-fp16 (17 JSON/total failures)
- `sroie_test/X51005663300`: json_valid=`True`, gt_total=`7.0`, pred_total=`7.4`, err=`None`
- `sroie_test/X51005719888`: json_valid=`True`, gt_total=`39.8`, pred_total=`42.06`, err=`None`
- `sroie_test/X51005746210`: json_valid=`False`, gt_total=`145.1`, pred_total=`None`, err=`unclosed_json_object`
- `sroie_test/X51006414702`: json_valid=`True`, gt_total=`157.9`, pred_total=`165.1`, err=`None`
- `sroie_test/X51006555833`: json_valid=`True`, gt_total=`1.52`, pred_total=`14.12`, err=`None`

### qwen35-4bit (20 JSON/total failures)
- `sroie_test/X51005663300`: json_valid=`True`, gt_total=`7.0`, pred_total=`7.4`, err=`None`
- `sroie_test/X51005746210`: json_valid=`False`, gt_total=`145.1`, pred_total=`None`, err=`unclosed_json_object`
- `sroie_test/X51006008092`: json_valid=`True`, gt_total=`30.7`, pred_total=`28.94`, err=`None`
- `sroie_test/X51006619506`: json_valid=`True`, gt_total=`23.55`, pred_total=`24.1`, err=`None`
- `sroie_test/X51006619760`: json_valid=`True`, gt_total=`29.1`, pred_total=`27.46`, err=`None`
