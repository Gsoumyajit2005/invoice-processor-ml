"""Lazy thread-safe Indra OCR 1.1 service returning normalized [0..1000] coordinates."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

import numpy as np

from app.core.config import Settings
from app.core.paths import INDRA_OCR_DIR, configure_local_caches
from app.extractors.base import OcrDocumentResult, OcrLine
from app.pdf.processor import ProcessedDocument


def _clamp_1000(val: float) -> float:
    return round(max(0.0, min(1000.0, val)), 2)


class IndraOcrService:
    """Lazy singleton wrapper around Indra OCR 1.1 ONNX Runtime pipeline."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._converter: Any | None = None

    def _get_converter(self) -> Any:
        if self._converter is None:
            with self._lock:
                if self._converter is None:
                    configure_local_caches(offline=self._settings.local_vlm_offline)
                    import indra_ocr

                    model_path = str(INDRA_OCR_DIR) if INDRA_OCR_DIR.exists() else None
                    self._converter = indra_ocr.load(
                        path=model_path,
                        threads=self._settings.ocr_threads,
                        dpi=self._settings.ocr_dpi,
                        mode="auto",
                    )
        return self._converter

    def run_sync(self, doc: ProcessedDocument) -> OcrDocumentResult:
        """Run Indra OCR sequentially across all rendered pages synchronously."""
        t0 = time.perf_counter()
        converter = self._get_converter()

        md_chunks: list[str] = []
        txt_chunks: list[str] = []
        all_lines: list[OcrLine] = []

        for page in doc.pages:
            gray = np.asarray(page.image.convert("L"), dtype=np.uint8)
            ocr_page = converter.ocr(gray)
            w = max(page.width, 1)
            h = max(page.height, 1)

            page_lines_txt: list[str] = []
            for line in ocr_page.lines:
                txt = (line.text or "").strip()
                if not txt:
                    continue
                bx0, by0, bx1, by1 = line.box
                all_lines.append(
                    OcrLine(
                        page=page.page_number,
                        text=txt,
                        x1=_clamp_1000((bx0 / w) * 1000.0),
                        y1=_clamp_1000((by0 / h) * 1000.0),
                        x2=_clamp_1000((bx1 / w) * 1000.0),
                        y2=_clamp_1000((by1 / h) * 1000.0),
                        confidence=round(float(max(0.0, min(1.0, line.conf))), 4),
                    )
                )
                page_lines_txt.append(txt)

            raw_page_md = (ocr_page.markdown or "").strip()
            if not raw_page_md:
                raw_page_md = "\n".join(page_lines_txt) or page.native_text
            if not raw_page_md and page.native_text:
                raw_page_md = page.native_text

            md_chunks.append(f"--- Page {page.page_number} ---\n{raw_page_md}".strip())
            txt_body = "\n".join(page_lines_txt) or page.native_text
            txt_chunks.append(f"--- Page {page.page_number} ---\n{txt_body}".strip())

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return OcrDocumentResult(
            markdown="\n\n".join(md_chunks),
            plain_text="\n\n".join(txt_chunks),
            lines=all_lines,
            latency_ms=latency_ms,
        )

    async def run(self, doc: ProcessedDocument) -> OcrDocumentResult:
        """Execute OCR without blocking the FastAPI event loop."""
        return await asyncio.to_thread(self.run_sync, doc)
