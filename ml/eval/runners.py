"""Model runners for Phase 1 benchmark: LayoutLMv3 baseline vs Indra OCR + VLMs."""

from __future__ import annotations

import gc
import importlib
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from eval.paths import (
    INDRA_OCR_DIR,
    LAYOUTLMV3_DOCTR_DIR,
    REPO_ROOT,
    configure_local_caches,
)
from eval.prompts import build_extraction_prompt
from eval.schemas import InvoiceExtraction, parse_extraction_output
from eval.temp_manifest import EvalSample

# Must run before importing transformers, doctr, indra_ocr, or torch caches.
configure_local_caches(offline=True)

import indra_ocr  # noqa: E402
import numpy as np  # noqa: E402
import pypdfium2 as pdfium  # noqa: E402
import torch  # noqa: E402
from doctr.models import ocr_predictor  # noqa: E402
from transformers import (  # noqa: E402
    AutoModelForImageTextToText,
    AutoProcessor,
    BitsAndBytesConfig,
    LayoutLMv3ForTokenClassification,
    LayoutLMv3Processor,
)


@dataclass
class RunnerResult:
    """Measured inference result for a single document."""

    prediction: InvoiceExtraction | None
    json_valid: bool
    latency_s: float
    ocr_latency_s: float
    model_latency_s: float
    peak_vram_mb: float
    raw_output: str
    ocr_chars: int = 0
    error: str | None = None


def render_pages(
    sample: EvalSample,
    *,
    dpi: float = 150.0,
    max_pages: int | None = None,
) -> list[Image.Image]:
    """Load RGB PIL images for an image or PDF sample."""
    if sample.image is not None:
        return [sample.image.convert("RGB")]
    if sample.path is None:
        raise ValueError(f"Sample {sample.sample_id} has neither path nor image")

    path = sample.path
    if path.suffix.lower() == ".pdf":
        doc = pdfium.PdfDocument(str(path))
        try:
            total = len(doc)
            limit = min(total, max_pages) if max_pages else total
            scale = dpi / 72.0
            pages = [
                doc[idx].render(scale=scale).to_pil().convert("RGB")  # type: ignore[arg-type]
                for idx in range(limit)
            ]
            return pages
        finally:
            doc.close()

    with Image.open(path) as img:
        return [img.convert("RGB")]


def resize_for_vlm(img: Image.Image, max_side: int = 1280) -> Image.Image:
    """Cap image long side to preserve legibility while bounding ViT VRAM on 6GB GPUs."""
    w, h = img.size
    longest = max(w, h)
    if longest <= max_side:
        return img
    scale = max_side / longest
    new_size = (max(1, round(w * scale)), max(1, round(h * scale)))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def select_vlm_pages(images: list[Image.Image], max_images: int = 3) -> list[Image.Image]:
    """Select representative pages (first pages + last page) for long PDFs."""
    if len(images) <= max_images:
        return images
    if max_images == 1:
        return [images[0]]
    # Keep first (header/items) + second + last (totals/summary)
    chosen = images[: max_images - 1] + [images[-1]]
    return chosen


def release_cuda() -> None:
    """Reclaim GPU memory cleanly between model runs."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.empty_cache()


class IndraOCRFrontEnd:
    """Shared CPU ONNX / PDF text-layer reader via local Indra OCR v1.1.0."""

    def __init__(self, *, threads: int = 4, dpi: float = 150.0) -> None:
        self.dpi = dpi
        self.converter = indra_ocr.load(
            path=INDRA_OCR_DIR,
            threads=threads,
            dpi=dpi,
            mode="auto",
        )

    def read_sample(
        self, sample: EvalSample, *, max_vlm_pages: int = 3
    ) -> tuple[str, list[Image.Image], float]:
        """Run Indra OCR across all pages and prepare bounded VLM images."""
        t0 = time.perf_counter()
        if sample.path is not None:
            pages_out = [page for _, page in self.converter.convert(sample.path)]
            raw_images = render_pages(sample, dpi=self.dpi)
        elif sample.image is not None:
            rgb = sample.image.convert("RGB")
            gray = np.asarray(rgb.convert("L"), dtype=np.uint8)
            pages_out = [self.converter.ocr(gray)]
            raw_images = [rgb]
        else:
            raise ValueError(f"Sample {sample.sample_id} missing input")

        sections: list[str] = []
        for idx, page in enumerate(pages_out, start=1):
            content = (page.markdown or page.text or "").strip()
            if content:
                prefix = f"--- Page {idx} ({page.source}) ---\n" if len(pages_out) > 1 else ""
                sections.append(prefix + content)
        ocr_text = "\n\n".join(sections)
        ocr_latency = time.perf_counter() - t0

        vlm_images = [
            resize_for_vlm(im) for im in select_vlm_pages(raw_images, max_images=max_vlm_pages)
        ]
        return ocr_text, vlm_images, ocr_latency


class BaselineLayoutLMv3Runner:
    """Legacy single-page DocTR + LayoutLMv3-doctr-trained + regex/table heuristic baseline."""

    name = "baseline_layoutlmv3_doctr"

    def __init__(self, device: str | None = None) -> None:
        if not LAYOUTLMV3_DOCTR_DIR.exists() or not (REPO_ROOT / "src").exists():
            raise RuntimeError(
                "Legacy v1 LayoutLMv3/src baseline artifacts were removed in v2 modernization; "
                "checkout git tag 'v1-legacy-layoutlmv3' to run the legacy baseline."
            )
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        self.legacy_extraction = importlib.import_module("src.extraction")
        table_mod = importlib.import_module("src.table_extraction")
        self.legacy_table_items = table_mod.extract_table_items

        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.ocr_model = ocr_predictor(
            det_arch="db_resnet50",
            reco_arch="crnn_vgg16_bn",
            pretrained=True,
        ).to(self.device)
        self.processor = LayoutLMv3Processor.from_pretrained(
            str(LAYOUTLMV3_DOCTR_DIR),
            apply_ocr=False,
            local_files_only=True,
        )
        lm_model: Any = LayoutLMv3ForTokenClassification.from_pretrained(
            str(LAYOUTLMV3_DOCTR_DIR),
            local_files_only=True,
        )
        lm_model.to(self.device)
        lm_model.eval()
        self.model = lm_model

    def _run_doctr(
        self, img: Image.Image
    ) -> tuple[list[str], list[list[int]], list[list[int]], str]:
        w, h = img.size
        np_img = np.asarray(img)
        result = self.ocr_model([np_img])
        words: list[str] = []
        boxes_norm: list[list[int]] = []
        boxes_px: list[list[int]] = []
        lines_text: list[str] = []

        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    line_words = []
                    for word in line.words:
                        (xmin, ymin), (xmax, ymax) = word.geometry
                        words.append(word.value)
                        line_words.append(word.value)
                        boxes_norm.append(
                            [
                                max(0, min(1000, int(xmin * 1000))),
                                max(0, min(1000, int(ymin * 1000))),
                                max(0, min(1000, int(xmax * 1000))),
                                max(0, min(1000, int(ymax * 1000))),
                            ]
                        )
                        px_x = int(xmin * w)
                        px_y = int(ymin * h)
                        px_w = max(1, int((xmax - xmin) * w))
                        px_h = max(1, int((ymax - ymin) * h))
                        boxes_px.append([px_x, px_y, px_w, px_h])
                    if line_words:
                        lines_text.append(" ".join(line_words))
        return words, boxes_norm, boxes_px, "\n".join(lines_text)

    def _predict_entities(
        self, img: Image.Image, words: list[str], boxes: list[list[int]]
    ) -> dict[str, str]:
        if not words:
            return {}
        encoding = self.processor(
            img,
            words,
            boxes=boxes,
            truncation=True,
            max_length=512,
            stride=128,
            return_overflowing_tokens=True,
            padding="max_length",
            return_tensors="pt",
        )
        word_votes: dict[int, str] = {}
        id2label: dict[int, str] = self.model.config.id2label or {}
        n_windows = encoding["input_ids"].shape[0]
        pv = encoding["pixel_values"]

        for win_idx in range(n_windows):
            pv_item = pv[win_idx]
            if not isinstance(pv_item, torch.Tensor):
                pv_item = torch.as_tensor(pv_item)
            if pv_item.ndim == 3:
                pv_item = pv_item.unsqueeze(0)
            inputs = {
                "input_ids": encoding["input_ids"][win_idx : win_idx + 1].to(self.device),
                "attention_mask": encoding["attention_mask"][win_idx : win_idx + 1].to(self.device),
                "bbox": encoding["bbox"][win_idx : win_idx + 1].to(self.device),
                "pixel_values": pv_item.to(self.device),
            }
            with torch.inference_mode():
                logits = self.model(**inputs).logits
            preds = logits.argmax(-1).squeeze(0).tolist()
            w_ids = encoding.word_ids(batch_index=win_idx)
            for tok_idx, word_idx in enumerate(w_ids):
                if word_idx is not None and word_idx not in word_votes:
                    word_votes[word_idx] = id2label[preds[tok_idx]]

        groups: dict[str, list[str]] = {}
        for idx, word in enumerate(words):
            tag = word_votes.get(idx, "O")
            if tag == "O" or "-" not in tag:
                continue
            ent_type = tag.split("-", 1)[1].lower()
            groups.setdefault(ent_type, []).append(word)
        return {k: " ".join(v) for k, v in groups.items()}

    def run(self, sample: EvalSample) -> RunnerResult:
        """Run DocTR + LayoutLMv3 + legacy regex/table heuristics on page 1."""
        t0 = time.perf_counter()
        if self.device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(self.device)

        try:
            pages = render_pages(sample, dpi=150.0, max_pages=1)
            img = pages[0]

            t_ocr0 = time.perf_counter()
            words, boxes_norm, boxes_px, full_text = self._run_doctr(img)
            ocr_latency = time.perf_counter() - t_ocr0

            t_m0 = time.perf_counter()
            ml_ents = self._predict_entities(img, words, boxes_norm)

            vendor = ml_ents.get("company") or self.legacy_extraction.extract_vendor(full_text)
            address = ml_ents.get("address") or self.legacy_extraction.extract_address(
                full_text, vendor
            )
            date_val = ml_ents.get("date")
            if not date_val:
                dates = self.legacy_extraction.extract_dates(full_text)
                date_val = dates[0] if dates else None

            total_val = ml_ents.get("total")
            if total_val is None:
                total_val = self.legacy_extraction.extract_total(full_text)

            inv_no = ml_ents.get("invoice_no") or self.legacy_extraction.extract_invoice_number(
                full_text
            )
            bill_raw = ml_ents.get("bill_to") or self.legacy_extraction.extract_bill_to(full_text)
            bill_to = bill_raw.get("name") if isinstance(bill_raw, dict) else bill_raw

            table_rows = self.legacy_table_items(words, boxes_px)
            if not table_rows:
                table_rows = self.legacy_extraction.extract_line_items(full_text)
            mapped_items = [
                {
                    "description": r.get("description", ""),
                    "quantity": r.get("quantity"),
                    "unit_price": r.get("unit_price"),
                    "total_price": r.get("total")
                    if r.get("total") is not None
                    else r.get("total_price"),
                }
                for r in table_rows
                if r.get("description")
            ]

            pred = InvoiceExtraction.model_validate(
                {
                    "vendor": vendor,
                    "vendor_address": address,
                    "receipt_number": inv_no,
                    "date": date_val,
                    "currency": None,
                    "subtotal": None,
                    "tax_amount": None,
                    "discount_amount": None,
                    "total_amount": total_val,
                    "bill_to": bill_to,
                    "line_items": mapped_items,
                }
            )
            model_latency = time.perf_counter() - t_m0

            peak_vram = (
                torch.cuda.max_memory_allocated(self.device) / (1024**2)
                if self.device.type == "cuda"
                else 0.0
            )
            return RunnerResult(
                prediction=pred,
                json_valid=True,
                latency_s=time.perf_counter() - t0,
                ocr_latency_s=ocr_latency,
                model_latency_s=model_latency,
                peak_vram_mb=peak_vram,
                raw_output=pred.model_dump_json(),
                ocr_chars=len(full_text),
            )
        except Exception as exc:  # noqa: BLE001
            return RunnerResult(
                prediction=None,
                json_valid=False,
                latency_s=time.perf_counter() - t0,
                ocr_latency_s=0.0,
                model_latency_s=0.0,
                peak_vram_mb=0.0,
                raw_output="",
                error=f"{type(exc).__name__}: {exc}",
            )

    def close(self) -> None:
        del self.ocr_model, self.model, self.processor
        release_cuda()


class IndraVLMRunner:
    """Two-stage runner: Indra OCR 1.1 -> multimodal VLM (Xiaomi-OCR-0 or Qwen3.5-0.8B)."""

    def __init__(
        self,
        *,
        name: str,
        model_dir: Path,
        indra: IndraOCRFrontEnd,
        precision: str = "bf16",
        use_ocr_context: bool = True,
        max_new_tokens: int = 1536,
        adapter_dir: Path | None = None,
    ) -> None:
        self.name = name
        self.model_dir = model_dir
        self.indra = indra
        self.precision = precision
        self.use_ocr_context = use_ocr_context
        self.max_new_tokens = max_new_tokens
        self.adapter_dir = adapter_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.processor = AutoProcessor.from_pretrained(
            str(model_dir),
            local_files_only=True,
        )
        if hasattr(self.processor, "image_processor") and hasattr(
            self.processor.image_processor, "size"
        ):
            self.processor.image_processor.size = {
                "shortest_edge": 65536,
                "longest_edge": 1024 * 1280,
            }

        load_kwargs: dict[str, Any] = {"local_files_only": True}
        if precision == "4bit":
            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            )
            load_kwargs["device_map"] = "auto"
            vlm_model: Any = AutoModelForImageTextToText.from_pretrained(
                str(model_dir), **load_kwargs
            )
            vlm_model.eval()
            self.model = vlm_model
        else:
            dtype = torch.bfloat16 if precision == "bf16" else torch.float16
            vlm_model: Any = AutoModelForImageTextToText.from_pretrained(
                str(model_dir),
                dtype=dtype,
                local_files_only=True,
            )
            if adapter_dir is not None:
                from peft import PeftModel

                vlm_model = PeftModel.from_pretrained(
                    vlm_model, str(adapter_dir)
                ).merge_and_unload()
            vlm_model.to(self.device)
            vlm_model.eval()
            self.model = vlm_model

    def run_with_ocr(
        self,
        sample: EvalSample,
        *,
        ocr_text: str,
        images: list[Image.Image],
        ocr_latency_s: float,
    ) -> RunnerResult:
        """Run VLM inference given precomputed Indra OCR output and bounded page images."""
        t0 = time.perf_counter()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        try:
            prompt = build_extraction_prompt(ocr_text if self.use_ocr_context else None)
            content: list[dict[str, Any]] = [{"type": "image", "image": im} for im in images]
            content.append({"type": "text", "text": prompt})
            messages = [{"role": "user", "content": content}]

            t_m0 = time.perf_counter()
            inputs = self.processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                enable_thinking=False,
                return_dict=True,
                return_tensors="pt",
            ).to(self.model.device)

            with torch.inference_mode():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                )

            if torch.cuda.is_available():
                torch.cuda.synchronize()
            model_latency = time.perf_counter() - t_m0

            gen_tokens = output_ids[:, inputs["input_ids"].shape[1] :]
            raw_text = self.processor.batch_decode(gen_tokens, skip_special_tokens=True)[0].strip()

            pred, json_valid, parse_err = parse_extraction_output(raw_text)
            peak_vram = (
                torch.cuda.max_memory_allocated() / (1024**2) if torch.cuda.is_available() else 0.0
            )
            return RunnerResult(
                prediction=pred,
                json_valid=json_valid,
                latency_s=ocr_latency_s
                + model_latency
                + (time.perf_counter() - t0 - model_latency),
                ocr_latency_s=ocr_latency_s,
                model_latency_s=model_latency,
                peak_vram_mb=peak_vram,
                raw_output=raw_text,
                ocr_chars=len(ocr_text),
                error=parse_err,
            )
        except Exception as exc:  # noqa: BLE001
            return RunnerResult(
                prediction=None,
                json_valid=False,
                latency_s=ocr_latency_s + (time.perf_counter() - t0),
                ocr_latency_s=ocr_latency_s,
                model_latency_s=0.0,
                peak_vram_mb=(
                    torch.cuda.max_memory_allocated() / (1024**2)
                    if torch.cuda.is_available()
                    else 0.0
                ),
                raw_output="",
                error=f"{type(exc).__name__}: {exc}",
            )

    def run(self, sample: EvalSample) -> RunnerResult:
        """Execute Indra OCR + VLM extraction on ``sample``."""
        try:
            ocr_text, images, ocr_latency = self.indra.read_sample(sample)
        except Exception as exc:  # noqa: BLE001
            return RunnerResult(
                prediction=None,
                json_valid=False,
                latency_s=0.0,
                ocr_latency_s=0.0,
                model_latency_s=0.0,
                peak_vram_mb=0.0,
                raw_output="",
                error=f"{type(exc).__name__}: {exc}",
            )
        return self.run_with_ocr(
            sample,
            ocr_text=ocr_text,
            images=images,
            ocr_latency_s=ocr_latency,
        )

    def close(self) -> None:
        del self.model, self.processor
        release_cuda()
