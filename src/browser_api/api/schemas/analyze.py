from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from browser_api.application.dto import (
    AnalyzeSelectionMetadata,
    AnalyzeTranslateCommand,
    AnalyzeTranslateResult,
    AnalyzeUsageMetrics,
    ModelCatalogResult,
)


class SelectionRectPayload(BaseModel):
    """Viewport-space rectangle copied from the content script snapshot."""

    left: float
    top: float
    width: float
    height: float


class SelectionMetadataPayload(BaseModel):
    """Optional page context carried through for diagnostics and future features."""

    url: str | None = None
    page_title: str | None = None
    viewport_width: float | None = None
    viewport_height: float | None = None
    device_pixel_ratio: float | None = None
    rect: SelectionRectPayload | None = None


class SelectionMetadataItemPayload(SelectionMetadataPayload):
    """Per-item batch metadata for reconstructing ordering and sparse image inclusion."""

    id: str | None = None
    order: int | None = None
    source: Literal["text-selection", "free-rectangle"] | None = None
    text: str | None = None
    include_image: bool | None = None
    image_index: int | None = None


class AnalyzeSelectionMetadataPayload(SelectionMetadataPayload):
    """Top-level selection metadata plus optional ordered batch item entries."""

    items: list[SelectionMetadataItemPayload] = Field(default_factory=list)


class AnalyzeTranslateRequest(BaseModel):
    """HTTP schema accepted from the browser extension."""

    text: str = ''
    model_name: str | None = None
    cache_name: str | None = None
    images: list[str] = Field(default_factory=list)
    mode: Literal["translation", "translation_with_explanation", "custom_prompt"] = "translation"
    custom_prompt: str | None = None
    selection_metadata: AnalyzeSelectionMetadataPayload | None = None

    @model_validator(mode="after")
    def validate_custom_prompt(self) -> "AnalyzeTranslateRequest":
        """Keep custom prompt validation at the HTTP boundary so the service sees a consistent command."""

        if self.mode == "custom_prompt" and not (self.custom_prompt and self.custom_prompt.strip()):
            raise ValueError("custom_prompt is required when mode=custom_prompt")
        if not self.text.strip() and len(self.images) == 0:
            raise ValueError(
                "At least one of non-empty text or one-or-more images is required"
            )
        return self

    def to_command(self) -> AnalyzeTranslateCommand:
        """Convert the transport schema into the application command used by AnalyzeService."""

        selection_metadata: AnalyzeSelectionMetadata | None = None
        if self.selection_metadata is not None:
            selection_metadata = self.selection_metadata.model_dump(
                mode="json", exclude_none=True
            )

        return AnalyzeTranslateCommand(
            text=self.text,
            model_name=self.model_name,
            cache_name=self.cache_name.strip() if self.cache_name else None,
            images=self.images,
            mode=self.mode,
            custom_prompt=self.custom_prompt.strip() if self.custom_prompt else None,
            selection_metadata=selection_metadata,
        )


class AnalyzeUsagePayload(BaseModel):
    prompt_token_count: int | None = None
    cached_content_token_count: int | None = None
    candidates_token_count: int | None = None
    total_token_count: int | None = None

    @classmethod
    def from_result(
        cls,
        result: AnalyzeUsageMetrics,
    ) -> "AnalyzeUsagePayload":
        return cls(
            prompt_token_count=result.prompt_token_count,
            cached_content_token_count=result.cached_content_token_count,
            candidates_token_count=result.candidates_token_count,
            total_token_count=result.total_token_count,
        )


class AnalyzeTranslateResponse(BaseModel):
    """HTTP response schema returned to the browser extension."""

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
    usage: AnalyzeUsagePayload | None = None
    cache_request_attempted: bool | None = None
    cache_request_failed: bool | None = None
    cache_fallback_reason: str | None = None

    @classmethod
    def from_result(
        cls,
        result: AnalyzeTranslateResult,
    ) -> "AnalyzeTranslateResponse":
        """Serialize the application result without exposing service internals."""

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
            usage=(
                AnalyzeUsagePayload.from_result(result.usage)
                if result.usage is not None
                else None
            ),
            cache_request_attempted=result.cache_request_attempted,
            cache_request_failed=result.cache_request_failed,
            cache_fallback_reason=result.cache_fallback_reason,
        )


class ModelPayload(BaseModel):
    """Transport form of a model option shown in the popup."""

    model_id: str
    display_name: str


class ModelListResponse(BaseModel):
    """Model catalog plus fallback metadata so the popup can explain degraded states."""

    ok: bool = True
    models: list[ModelPayload]
    source: Literal["live", "config_fallback"]
    availability: Literal["live", "degraded"]
    detail: str | None = None
    degraded_reason: str | None = None

    @classmethod
    def from_result(cls, result: ModelCatalogResult) -> "ModelListResponse":
        """Serialize application model catalog results for the popup."""

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