from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from browser_api.api.app import create_app
from browser_api.api.dependencies import BrowserAPIServices, get_services
from browser_api.application.dto import AnalyzeTranslateResult, ModelCatalogResult
from pdf_epub_reader.dto import ModelInfo


@dataclass
class StubAnalyzeService:
    """Test double that isolates router tests from real AnalyzeService and AIModel wiring."""

    result: AnalyzeTranslateResult | None = None
    models_result: ModelCatalogResult | None = None
    error: Exception | None = None
    model_error: Exception | None = None
    calls: list[Any] | None = None
    model_calls: int = 0

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
def stub_analyze_service(
    analyze_result: AnalyzeTranslateResult,
    models_result: ModelCatalogResult,
) -> StubAnalyzeService:
    return StubAnalyzeService(result=analyze_result, models_result=models_result, calls=[])


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