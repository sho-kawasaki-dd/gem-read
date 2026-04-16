from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pdf_epub_reader.dto import ModelInfo


@dataclass(frozen=True, slots=True)
class AnalyzeTranslateCommand:
    """Application-layer request detached from HTTP schema and transport details."""

    text: str
    model_name: str | None
    images: list[str]
    mode: Literal["translation", "translation_with_explanation", "custom_prompt"]
    custom_prompt: str | None = None
    selection_metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AnalyzeTranslateResult:
    """Normalized analyze result returned by the service before HTTP serialization."""

    mode: Literal["translation", "translation_with_explanation", "custom_prompt"]
    translated_text: str
    explanation: str | None
    raw_response: str
    used_mock: bool
    image_count: int
    availability: Literal["live", "mock"] = "live"
    degraded_reason: str | None = None
    selection_metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ModelCatalogResult:
    """Model list plus availability metadata for degraded popup states."""

    models: list[ModelInfo]
    source: Literal["live", "config_fallback"]
    availability: Literal["live", "degraded"]
    detail: str | None = None
    degraded_reason: str | None = None