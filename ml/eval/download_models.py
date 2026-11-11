"""Download all benchmark models and datasets strictly inside the repository."""

from __future__ import annotations

import shutil
from pathlib import Path

from eval.paths import (
    CACHE_DIR,
    DOCTR_MODELS_DIR,
    INDRA_OCR_DIR,
    LAYOUTLMV3_DOCTR_DIR,
    MODELS_DIR,
    QWEN35_08B_DIR,
    XIAOMI_OCR_DIR,
    configure_local_caches,
)

# Force all cache env vars inside <repo>/.cache before importing HF/DocTR/Indra.
configure_local_caches()

import indra_ocr  # noqa: E402
from datasets import load_dataset  # noqa: E402
from doctr.models import ocr_predictor  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402

VLM_PATTERNS = [
    "*.json",
    "*.safetensors",
    "*.jinja",
    "*.txt",
    "merges.txt",
    "README.md",
    "LICENSE*",
]

INDRA_PATTERNS = [
    "*.onnx",
    "meta.json",
    "lm.npz",
    "lm_*.npz",
    "README.md",
    "LICENSE*",
]

INDRA_MATH_IGNORE = [
    "mathcls.onnx",
    "math_enc.onnx",
    "math_dec_init.onnx",
    "math_dec_step.onnx",
    "math_meta.json",
]


def dir_size_mb(path: Path) -> float:
    """Return recursive directory size in MiB."""
    if not path.exists():
        return 0.0
    total = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    return total / (1024 * 1024)


def download_snapshot(
    repo_id: str,
    target_dir: Path,
    *,
    revision: str = "main",
    allow_patterns: list[str] | None = None,
    ignore_patterns: list[str] | None = None,
) -> Path:
    """Download a Hugging Face repository directly into ``target_dir``."""
    target_dir.mkdir(parents=True, exist_ok=True)
    tmp_cache = CACHE_DIR / "hf_download_tmp"
    tmp_cache.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=repo_id,
        revision=revision,
        local_dir=str(target_dir),
        cache_dir=str(tmp_cache),
        allow_patterns=allow_patterns,
        ignore_patterns=ignore_patterns,
    )
    if tmp_cache.exists():
        shutil.rmtree(tmp_cache, ignore_errors=True)
    return target_dir


def main() -> None:
    """Download all Phase 1 models and eval datasets into ./models and ./.cache."""
    # Clean leftover staging folder from earlier config probe.
    hf_hub_cache = CACHE_DIR / "hf_hub"
    if hf_hub_cache.exists():
        shutil.rmtree(hf_hub_cache, ignore_errors=True)
        hf_hub_cache.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Xiaomi-OCR-0 -> {XIAOMI_OCR_DIR}")
    download_snapshot(
        "xiaomi-research/Xiaomi-OCR-0",
        XIAOMI_OCR_DIR,
        revision="main",
        allow_patterns=VLM_PATTERNS,
    )

    print(f"Downloading Qwen3.5-0.8B -> {QWEN35_08B_DIR}")
    download_snapshot(
        "Qwen/Qwen3.5-0.8B",
        QWEN35_08B_DIR,
        revision="main",
        allow_patterns=VLM_PATTERNS,
    )

    print(f"Downloading Indra OCR v1.1.0 -> {INDRA_OCR_DIR}")
    download_snapshot(
        "datalab-to/indra-ocr",
        INDRA_OCR_DIR,
        revision="v1.1.0",
        allow_patterns=INDRA_PATTERNS,
        ignore_patterns=INDRA_MATH_IGNORE,
    )

    print(f"Downloading DocTR weights -> {DOCTR_MODELS_DIR}")
    _ = ocr_predictor(
        det_arch="db_resnet50",
        reco_arch="crnn_vgg16_bn",
        pretrained=True,
    )

    print("Verifying local Indra OCR load...")
    _ = indra_ocr.load(path=INDRA_OCR_DIR)

    print("Downloading naver-clova-ix/cord-v2 validation & test splits -> ./.cache/hf_datasets")
    cord_val = load_dataset("naver-clova-ix/cord-v2", split="validation")
    cord_test = load_dataset("naver-clova-ix/cord-v2", split="test")
    print(f"CORD-v2 loaded: validation={len(cord_val)}, test={len(cord_test)}")

    print("\nLocal model directory sizes (MiB):")
    for folder in sorted(MODELS_DIR.iterdir()):
        if folder.is_dir():
            print(f"  {folder.name:28s} {dir_size_mb(folder):8.1f} MiB")

    print("\nBaseline LayoutLMv3 folder check:", LAYOUTLMV3_DOCTR_DIR.exists())


if __name__ == "__main__":
    main()
