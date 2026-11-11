"""OCR, local Qwen3.5 VLM, cloud LiteLLM escalation, grounding, and routing."""

from app.extractors.base import (
    CloudConfig,
    ExtractionRunResult,
    ExtractorBackend,
    OcrDocumentResult,
    OcrLine,
    build_v2_extraction_prompt,
)
from app.extractors.cloud_vlm import CloudConfigError, CloudVlmExtractor
from app.extractors.grounding import ground_extraction
from app.extractors.indra_service import IndraOcrService
from app.extractors.local_vlm import LocalVlmExtractor, LocalVlmUnavailableError
from app.extractors.router import ExtractionRouter

__all__ = [
    "CloudConfig",
    "CloudConfigError",
    "CloudVlmExtractor",
    "ExtractionRouter",
    "ExtractionRunResult",
    "ExtractorBackend",
    "IndraOcrService",
    "LocalVlmExtractor",
    "LocalVlmUnavailableError",
    "OcrDocumentResult",
    "OcrLine",
    "build_v2_extraction_prompt",
    "ground_extraction",
]
