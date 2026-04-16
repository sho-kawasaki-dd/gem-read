from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class AnalyzeTranslateCommand:
    text: str
    model_name: str | None
    images: list[str]
    mode: Literal["translation", "translation_with_explanation"]
    selection_metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AnalyzeTranslateResult:
    mode: str
    translated_text: str
    explanation: str | None
    raw_response: str
    used_mock: bool
    image_count: int
    selection_metadata: dict[str, Any] | None = None