from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from browser_api.application.dto import (
    AnalyzeTranslateCommand,
    AnalyzeTranslateResult,
    ModelCatalogResult,
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
    mode: Literal["translation", "translation_with_explanation", "custom_prompt"] = "translation"
    custom_prompt: str | None = None
    selection_metadata: SelectionMetadataPayload | None = None

    @model_validator(mode="after")
    def validate_custom_prompt(self) -> "AnalyzeTranslateRequest":
        if self.mode == "custom_prompt" and not (self.custom_prompt and self.custom_prompt.strip()):
            raise ValueError("custom_prompt is required when mode=custom_prompt")
        return self

    def to_command(self) -> AnalyzeTranslateCommand:
        selection_metadata: dict[str, Any] | None = None
        if self.selection_metadata is not None:
            selection_metadata = self.selection_metadata.model_dump(mode="json")

        return AnalyzeTranslateCommand(
            text=self.text,
            model_name=self.model_name,
            images=self.images,
            mode=self.mode,
            custom_prompt=self.custom_prompt.strip() if self.custom_prompt else None,
            selection_metadata=selection_metadata,
        )


class AnalyzeTranslateResponse(BaseModel):
    ok: bool = True
    mode: Literal["translation", "translation_with_explanation", "custom_prompt"]
    translated_text: str
    explanation: str | None = None
    raw_response: str
    used_mock: bool = False
    image_count: int = 0
    availability: Literal["live", "mock"] = "live"
    degraded_reason: str | None = None
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
            availability=result.availability,
            degraded_reason=result.degraded_reason,
            selection_metadata=result.selection_metadata,
        )


class ModelPayload(BaseModel):
    model_id: str
    display_name: str


class ModelListResponse(BaseModel):
    ok: bool = True
    models: list[ModelPayload]
    source: Literal["live", "config_fallback"]
    availability: Literal["live", "degraded"]
    detail: str | None = None
    degraded_reason: str | None = None

    @classmethod
    def from_result(cls, result: ModelCatalogResult) -> "ModelListResponse":
        return cls(
            models=[
                ModelPayload(
                    model_id=model.model_id,
                    display_name=model.display_name,
                )
                for model in result.models
            ],
            source=result.source,
            availability=result.availability,
            detail=result.detail,
            degraded_reason=result.degraded_reason,
        )