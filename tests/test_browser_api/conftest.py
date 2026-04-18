from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from browser_api.api.app import create_app
from browser_api.api.dependencies import BrowserAPIServices, get_services
from browser_api.application.dto import (
    AnalyzeTranslateResult,
    AnalyzeUsageMetrics,
    CacheDeleteResult,
    CacheStatusResult,
    ModelCatalogResult,
    TokenCountResult,
)
from pdf_epub_reader.dto import ModelInfo


@dataclass
class StubAnalyzeService:
    """Test double that isolates router tests from real AnalyzeService and AIModel wiring."""

    result: AnalyzeTranslateResult | None = None
    models_result: ModelCatalogResult | None = None
    error: Exception | None = None
    model_error: Exception | None = None
    cache_create_result: CacheStatusResult | None = None
    cache_status_result: CacheStatusResult | None = None
    cache_delete_result: CacheDeleteResult | None = None
    token_result: TokenCountResult | None = None
    cache_create_error: Exception | None = None
    cache_status_error: Exception | None = None
    cache_delete_error: Exception | None = None
    token_error: Exception | None = None
    calls: list[Any] | None = None
    model_calls: int = 0
    cache_create_calls: list[Any] | None = None
    cache_status_calls: int = 0
    cache_delete_calls: list[str] | None = None
    token_calls: list[Any] | None = None

    async def analyze_translate(self, command):
        if self.calls is not None:
            self.calls.append(command)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result

    async def list_models(self):
        self.model_calls += 1
        if self.model_error is not None:
            raise self.model_error
        assert self.models_result is not None
        return self.models_result

    async def create_cache(self, command):
        if self.cache_create_calls is not None:
            self.cache_create_calls.append(command)
        if self.cache_create_error is not None:
            raise self.cache_create_error
        assert self.cache_create_result is not None
        return self.cache_create_result

    async def get_cache_status(self):
        self.cache_status_calls += 1
        if self.cache_status_error is not None:
            raise self.cache_status_error
        assert self.cache_status_result is not None
        return self.cache_status_result

    async def delete_cache(self, cache_name: str):
        if self.cache_delete_calls is not None:
            self.cache_delete_calls.append(cache_name)
        if self.cache_delete_error is not None:
            raise self.cache_delete_error
        assert self.cache_delete_result is not None
        return self.cache_delete_result

    async def count_tokens(self, command):
        if self.token_calls is not None:
            self.token_calls.append(command)
        if self.token_error is not None:
            raise self.token_error
        assert self.token_result is not None
        return self.token_result


@pytest.fixture
def analyze_result() -> AnalyzeTranslateResult:
    return AnalyzeTranslateResult(
        mode="translation",
        translated_text="こんにちは",
        explanation=None,
        raw_response="こんにちは",
        used_mock=False,
        image_count=1,
        availability="live",
        degraded_reason=None,
        selection_metadata={"url": "https://example.com"},
        usage=AnalyzeUsageMetrics(
            prompt_token_count=42,
            cached_content_token_count=1600,
            candidates_token_count=73,
            total_token_count=1715,
        ),
    )


@pytest.fixture
def models_result() -> ModelCatalogResult:
    return ModelCatalogResult(
        models=[ModelInfo(model_id="gemini-2.5-flash", display_name="Gemini 2.5 Flash")],
        source="live",
        availability="live",
        detail=None,
        degraded_reason=None,
    )


@pytest.fixture
def cache_status_result() -> CacheStatusResult:
    return CacheStatusResult(
        is_active=True,
        ttl_seconds=3600,
        token_count=2048,
        cache_name="cachedContents/abc123",
        display_name="example-article",
        model_name="gemini-2.5-flash",
        expire_time="2026-04-17T10:00:00+00:00",
    )


@pytest.fixture
def cache_delete_result() -> CacheDeleteResult:
    return CacheDeleteResult(cache_name="cachedContents/abc123")


@pytest.fixture
def token_count_result() -> TokenCountResult:
    return TokenCountResult(token_count=321, model_name="gemini-2.5-flash")


@pytest.fixture
def stub_analyze_service(
    analyze_result: AnalyzeTranslateResult,
    models_result: ModelCatalogResult,
    cache_status_result: CacheStatusResult,
    cache_delete_result: CacheDeleteResult,
    token_count_result: TokenCountResult,
) -> StubAnalyzeService:
    return StubAnalyzeService(
        result=analyze_result,
        models_result=models_result,
        cache_create_result=cache_status_result,
        cache_status_result=cache_status_result,
        cache_delete_result=cache_delete_result,
        token_result=token_count_result,
        calls=[],
        cache_create_calls=[],
        cache_delete_calls=[],
        token_calls=[],
    )


@pytest.fixture
def api_client(stub_analyze_service: StubAnalyzeService) -> TestClient:
    app = create_app()
    # router test では app state の依存だけ差し替え、HTTP 境界の検証対象を最小化する。
    app.dependency_overrides[get_services] = lambda: BrowserAPIServices(
        analyze_service=stub_analyze_service
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()