"""Tests for LoRA adapter configuration, default resolution, and fallback readiness."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.core.paths import REPO_ROOT
from app.extractors.local_vlm import LocalVlmExtractor


def test_resolved_adapter_dir_default_override_and_missing(tmp_path: Path) -> None:
    s_default = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s_default.local_vlm_adapter_dir == "models/qwen35-0.8b-invoice-lora"
    assert s_default.resolved_adapter_dir == REPO_ROOT / "models/qwen35-0.8b-invoice-lora"

    s_none = Settings(local_vlm_adapter_dir=None, _env_file=None)  # type: ignore[call-arg]
    assert s_none.resolved_adapter_dir is None

    s_rel = Settings(
        local_vlm_adapter_dir="models/nonexistent-lora",
        _env_file=None,  # type: ignore[call-arg]
    )
    assert s_rel.resolved_adapter_dir == REPO_ROOT / "models/nonexistent-lora"

    missing_model = tmp_path / "nonexistent-model"
    extractor = LocalVlmExtractor(s_rel, model_dir=missing_model)
    assert extractor.is_available() is False
    status = extractor.warmup_status()
    assert status["adapter_configured"] is True
    assert status["loaded"] is False
