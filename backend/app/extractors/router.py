"""Hybrid OCR + VLM extraction router with reconciliation-driven cloud escalation."""

from __future__ import annotations

import logging
import time
from typing import Literal

from app.core.config import Settings
from app.core.reconciliation import ReconciliationResult, reconcile_invoice
from app.core.schemas import InvoiceExtraction
from app.extractors.base import (
    CloudConfig,
    ExtractionRunResult,
    ExtractorBackend,
)
from app.extractors.cloud_vlm import CloudConfigError, CloudVlmExtractor
from app.extractors.grounding import ground_extraction
from app.extractors.hf_zerogpu import HfZerogpuExtractor
from app.extractors.indra_service import IndraOcrService
from app.extractors.local_vlm import LocalVlmExtractor, LocalVlmUnavailableError
from app.pdf.processor import ProcessedDocument

logger = logging.getLogger(__name__)


def _dedupe_warnings(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for grp in groups:
        for item in grp:
            if item not in seen:
                seen.add(item)
                merged.append(item)
    return merged


def _score_candidate(ext: InvoiceExtraction, rec: ReconciliationResult) -> tuple[int, int, int]:
    """Higher tuple is better: clean reconciliation > has total > populated fields."""
    clean_reconcile = 0 if rec.needs_escalation else 1
    has_total = 1 if ext.total_amount is not None else 0
    populated = sum(
        bool(getattr(ext, k))
        for k in ("vendor", "receipt_number", "date", "subtotal", "tax_amount")
    ) + len(ext.line_items)
    return (clean_reconcile, has_total, populated)


class ExtractionRouter:
    """Orchestrates Indra OCR -> Local Qwen3.5 / Cloud VLM -> Grounding -> Reconciliation."""

    def __init__(
        self,
        settings: Settings,
        *,
        ocr_service: IndraOcrService | None = None,
        local_extractor: ExtractorBackend | None = None,
        cloud_extractor: ExtractorBackend | None = None,
    ) -> None:
        self._settings = settings
        self.ocr_service = ocr_service or IndraOcrService(settings)
        if local_extractor is not None:
            self.local_extractor = local_extractor
        elif settings.extractor_default_mode == "hf_zerogpu":
            self.local_extractor = HfZerogpuExtractor(settings)
        else:
            local_candidate = LocalVlmExtractor(settings)
            if local_candidate.is_available():
                self.local_extractor = local_candidate
            elif getattr(settings, "hf_zerogpu_space", None):
                self.local_extractor = HfZerogpuExtractor(settings)
            else:
                self.local_extractor = local_candidate
        self.cloud_extractor = cloud_extractor or CloudVlmExtractor(settings)

    def _cloud_available(self, cloud_config: CloudConfig | None) -> bool:
        if isinstance(self.cloud_extractor, CloudVlmExtractor):
            return self.cloud_extractor.has_credentials(cloud_config)
        return bool(
            (cloud_config and cloud_config.api_key) or self._settings.default_cloud_api_key
        )

    def _cloud_label(self, cloud_config: CloudConfig | None) -> str:
        if isinstance(self.cloud_extractor, CloudVlmExtractor):
            try:
                model, _ = self.cloud_extractor.resolve_credentials(cloud_config)
                return f"cloud:{model}"
            except CloudConfigError:
                pass
        return getattr(self.cloud_extractor, "name", "cloud:litellm")

    async def run(
        self,
        doc: ProcessedDocument,
        *,
        mode: Literal["auto", "local", "cloud"] | None = None,
        cloud_config: CloudConfig | None = None,
    ) -> ExtractionRunResult:
        """Execute OCR, structured VLM extraction, optional escalation, and visual grounding."""
        t0 = time.perf_counter()
        effective_mode = mode or self._settings.extractor_default_mode
        ocr = await self.ocr_service.run(doc)

        chosen_extraction: InvoiceExtraction | None = None
        chosen_reconciliation: ReconciliationResult | None = None
        raw_output = ""
        extractor_used = ""

        if effective_mode == "cloud":
            chosen_extraction, raw_output = await self.cloud_extractor.extract(
                doc, ocr, cloud_config=cloud_config
            )
            chosen_reconciliation = reconcile_invoice(chosen_extraction, ocr_text=ocr.plain_text)
            extractor_used = self._cloud_label(cloud_config)

        elif effective_mode == "local":
            chosen_extraction, raw_output = await self.local_extractor.extract(
                doc, ocr, cloud_config=cloud_config
            )
            chosen_reconciliation = reconcile_invoice(chosen_extraction, ocr_text=ocr.plain_text)
            extractor_used = getattr(self.local_extractor, "name", "local")

        else:  # "auto"
            local_failed = False
            local_available = (
                self.local_extractor.is_available()
                if isinstance(self.local_extractor, LocalVlmExtractor)
                else True
            )

            if local_available:
                try:
                    local_ext, local_raw = await self.local_extractor.extract(
                        doc, ocr, cloud_config=cloud_config
                    )
                    local_rec = reconcile_invoice(local_ext, ocr_text=ocr.plain_text)
                    chosen_extraction = local_ext
                    chosen_reconciliation = local_rec
                    raw_output = local_raw
                    extractor_used = getattr(self.local_extractor, "name", "local")
                except LocalVlmUnavailableError as exc:
                    logger.warning("Local VLM unavailable during auto routing: %s", exc)
                    local_failed = True
            else:
                local_failed = True

            should_escalate = local_failed or (
                chosen_reconciliation is not None and chosen_reconciliation.needs_escalation
            )
            if should_escalate and self._cloud_available(cloud_config):
                cloud_ext, cloud_raw = await self.cloud_extractor.extract(
                    doc, ocr, cloud_config=cloud_config
                )
                cloud_rec = reconcile_invoice(cloud_ext, ocr_text=ocr.plain_text)
                if chosen_extraction is None or chosen_reconciliation is None:
                    chosen_extraction = cloud_ext
                    chosen_reconciliation = cloud_rec
                    raw_output = cloud_raw
                    extractor_used = self._cloud_label(cloud_config)
                elif _score_candidate(cloud_ext, cloud_rec) >= _score_candidate(
                    chosen_extraction, chosen_reconciliation
                ):
                    chosen_extraction = cloud_ext
                    chosen_reconciliation = cloud_rec
                    raw_output = cloud_raw
                    extractor_used = f"{extractor_used}->{self._cloud_label(cloud_config)}"
            elif chosen_extraction is None:
                raise LocalVlmUnavailableError(
                    "Local VLM is unavailable and no Cloud VLM API key is configured."
                )

        assert chosen_extraction is not None
        assert chosen_reconciliation is not None

        grounded = ground_extraction(chosen_extraction, ocr.lines)
        merged_warnings = _dedupe_warnings(
            grounded.validation_warnings,
            chosen_reconciliation.warnings,
        )
        grounded = grounded.model_copy(update={"validation_warnings": merged_warnings})

        total_ms = int((time.perf_counter() - t0) * 1000)
        return ExtractionRunResult(
            extraction=grounded,
            extractor_used=extractor_used,
            ocr=ocr,
            reconciliation=chosen_reconciliation,
            latency_ms=total_ms,
            raw_model_output=raw_output,
        )
