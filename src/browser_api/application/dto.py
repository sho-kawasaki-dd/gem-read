from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pdf_epub_reader.dto import ModelInfo


@dataclass(frozen=True, slots=True)
class AnalyzeTranslateCommand:
    text: str
    model_name: str | None
    images: list[str]
    mode: Literal["translation", "translation_with_explanation", "custom_prompt"]
    custom_prompt: str | None = None
    selection_metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AnalyzeTranslateResult:
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
    models: list[ModelInfo]
    source: Literal["live", "config_fallback"]
    availability: Literal["live", "degraded"]
    detail: str | None = None
    degraded_reason: str | None = None