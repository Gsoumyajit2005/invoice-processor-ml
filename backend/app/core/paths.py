"""Repository paths and local-only cache/model directory configuration."""

from __future__ import annotations

import os
from pathlib import Path

# backend/app/core/paths.py -> parents[3] is repository root
REPO_ROOT: Path = Path(__file__).resolve().parents[3]
BACKEND_DIR: Path = REPO_ROOT / "backend"
MODELS_DIR: Path = REPO_ROOT / "models"
CACHE_DIR: Path = REPO_ROOT / ".cache"

QWEN35_08B_DIR: Path = MODELS_DIR / "Qwen3.5-0.8B"
QWEN35_LORA_DIR: Path = MODELS_DIR / "qwen35-0.8b-invoice-lora"
XIAOMI_OCR_DIR: Path = MODELS_DIR / "Xiaomi-OCR-0"
INDRA_OCR_DIR: Path = MODELS_DIR / "indra-ocr"
DOCTR_MODELS_DIR: Path = MODELS_DIR / "doctr"
LAYOUTLMV3_DOCTR_DIR: Path = MODELS_DIR / "layoutlmv3-doctr-trained"


def configure_local_caches(*, offline: bool = False) -> dict[str, str]:
    """Force Hugging Face, PyTorch, Indra OCR, and XDG caches strictly inside this repo."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    env_map = {
        "HF_HOME": str(CACHE_DIR / "huggingface"),
        "HF_HUB_CACHE": str(CACHE_DIR / "hf_hub"),
        "HF_DATASETS_CACHE": str(CACHE_DIR / "hf_datasets"),
        "TORCH_HOME": str(CACHE_DIR / "torch"),
        "INDRA_OCR_MODEL_DIR": str(INDRA_OCR_DIR),
        "XDG_CACHE_HOME": str(CACHE_DIR / "xdg"),
    }
    for key, val in env_map.items():
        Path(val).mkdir(parents=True, exist_ok=True)
        os.environ[key] = val

    if offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"
    return env_map
