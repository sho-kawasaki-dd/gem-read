from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from browser_api.application.dto import (
    AnalyzeTranslateCommand,
    AnalyzeTranslateResult,
)


class SelectionRectPayload(BaseModel):
    left: float
    top: float
    width: float
    height: float


class SelectionMetadataPayload(BaseModel):
    url: str | None = None
    page_title: str | None = None
    viewport_width: float | None = None
    viewport_height: float | None = None
    device_pixel_ratio: float | None = None
    rect: SelectionRectPayload | None = None


class AnalyzeTranslateRequest(BaseModel):
    text: str = Field(min_length=1)
    model_name: str | None = None
    images: list[str] = Field(default_factory=list)
    mode: Literal["translation", "translation_with_explanation"] = "translation"
    selection_metadata: SelectionMetadataPayload | None = None

    def to_command(self) -> AnalyzeTranslateCommand:
        selection_metadata: dict[str, Any] | None = None
        if self.selection_metadata is not None:
            selection_metadata = self.selection_metadata.model_dump(mode="json")

        return AnalyzeTranslateCommand(
            text=self.text,
            model_name=self.model_name,
            images=self.images,
            mode=self.mode,
            selection_metadata=selection_metadata,
        )


class AnalyzeTranslateResponse(BaseModel):
    ok: bool = True
    mode: str
    translated_text: str
    explanation: str | None = None
    raw_response: str
    used_mock: bool = False
    image_count: int = 0
    selection_metadata: dict[str, Any] | None = None

    @classmethod
    def from_result(
        cls,
        result: AnalyzeTranslateResult,
    ) -> "AnalyzeTranslateResponse":
        return cls(
            mode=result.mode,
            translated_text=result.translated_text,
            explanation=result.explanation,
            raw_response=result.raw_response,
            used_mock=result.used_mock,
            image_count=result.image_count,
            selection_metadata=result.selection_metadata,
        )