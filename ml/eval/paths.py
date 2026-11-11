"""Repository paths and local cache configuration delegated to backend app.core.paths."""

from __future__ import annotations

import os

from app.core.paths import (
    CACHE_DIR,
    DOCTR_MODELS_DIR,
    INDRA_OCR_DIR,
    LAYOUTLMV3_DOCTR_DIR,
    MODELS_DIR,
    QWEN35_08B_DIR,
    REPO_ROOT,
    XIAOMI_OCR_DIR,
)
from app.core.paths import configure_local_caches as _configure_backend_caches

__all__ = [
    "REPO_ROOT",
    "MODELS_DIR",
    "CACHE_DIR",
    "QWEN35_08B_DIR",
    "XIAOMI_OCR_DIR",
    "INDRA_OCR_DIR",
    "DOCTR_MODELS_DIR",
    "LAYOUTLMV3_DOCTR_DIR",
    "configure_local_caches",
]


def configure_local_caches(*, offline: bool = False) -> dict[str, str]:
    """Configure backend caches plus legacy DocTR cache path for evaluation scripts."""
    env_map = _configure_backend_caches(offline=offline)
    DOCTR_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["DOCTR_CACHE_DIR"] = str(DOCTR_MODELS_DIR)
    env_map["DOCTR_CACHE_DIR"] = str(DOCTR_MODELS_DIR)
    return env_map
