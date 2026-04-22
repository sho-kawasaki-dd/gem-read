from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

from pdf_epub_reader.dto import ModelInfo


class AnalyzeSelectionRect(TypedDict):
    left: float
    top: float
    width: float
    height: float


class AnalyzeSelectionMetadataItem(TypedDict, total=False):
    id: str
    order: int
    source: Literal["text-selection", "free-rectangle"]
    text: str
    include_image: bool
    image_index: int | None
    url: str | None
    page_title: str | None
    viewport_width: float | None
    viewport_height: float | None
    device_pixel_ratio: float | None
    rect: AnalyzeSelectionRect | None


class AnalyzeSelectionMetadata(TypedDict, total=False):
    url: str | None
    page_title: str | None
    viewport_width: float | None
    viewport_height: float | None
    device_pixel_ratio: float | None
    rect: AnalyzeSelectionRect | None
    items: list[AnalyzeSelectionMetadataItem]


@dataclass(frozen=True, slots=True)
class AnalyzeTranslateCommand:
    """Application-layer request detached from HTTP schema and transport details."""

    text: str
    model_name: str | None
    images: list[str]
    mode: Literal["translation", "translation_with_explanation", "custom_prompt"]
    cache_name: str | None = None
    custom_prompt: str | None = None
    system_prompt: str | None = None
    selection_metadata: AnalyzeSelectionMetadata | None = None


@dataclass(frozen=True, slots=True)
class AnalyzeUsageMetrics:
    """Usage metadata exposed by browser_api for overlay token UX."""

    prompt_token_count: int | None = None
    cached_content_token_count: int | None = None
    candidates_token_count: int | None = None
    total_token_count: int | None = None


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
    selection_metadata: AnalyzeSelectionMetadata | None = None
    usage: AnalyzeUsageMetrics | None = None
    cache_request_attempted: bool | None = None
    cache_request_failed: bool | None = None
    cache_fallback_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ModelCatalogResult:
    """Model list plus availability metadata for degraded popup states."""

    models: list[ModelInfo]
    source: Literal["live", "config_fallback"]
    availability: Literal["live", "degraded"]
    detail: str | None = None
    degraded_reason: str | None = None


@dataclass(frozen=True, slots=True)
class CacheCreateCommand:
    """Application-layer request for creating a single active context cache."""

    full_text: str
    model_name: str | None
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class CacheStatusResult:
    """Normalized cache status exposed by browser_api."""

    is_active: bool = False
    ttl_seconds: int | None = None
    token_count: int | None = None
    cache_name: str | None = None
    display_name: str | None = None
    model_name: str | None = None
    expire_time: str | None = None


@dataclass(frozen=True, slots=True)
class CacheDeleteResult:
    """Deletion acknowledgement returned after a cache delete request."""

    cache_name: str


@dataclass(frozen=True, slots=True)
class CacheListItem:
    """Metadata for a single browser-extension-owned cache."""

    cache_name: str
    display_name: str
    model_name: str
    expire_time: str | None = None
    token_count: int | None = None


@dataclass(frozen=True, slots=True)
class CacheListResult:
    """Ordered list of browser-extension caches returned to the popup debug section."""

    items: list[CacheListItem]


@dataclass(frozen=True, slots=True)
class TokenCountCommand:
    """Application-layer request for token preflight estimation."""

    text: str
    model_name: str | None


@dataclass(frozen=True, slots=True)
class TokenCountResult:
    """Normalized token counting result for extension UX."""

    token_count: int
    model_name: str