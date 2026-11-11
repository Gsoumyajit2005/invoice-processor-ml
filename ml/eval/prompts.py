"""Canonical structured extraction prompts delegated to backend app.extractors.base."""

from __future__ import annotations

from app.extractors.base import (
    SCHEMA_TEMPLATE_V2 as SCHEMA_TEMPLATE,
)
from app.extractors.base import (
    build_v2_extraction_prompt as build_extraction_prompt,
)

__all__ = ["SCHEMA_TEMPLATE", "build_extraction_prompt"]
