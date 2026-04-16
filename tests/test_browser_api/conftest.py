from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from browser_api.api.app import create_app
from browser_api.api.dependencies import BrowserAPIServices, get_services
from browser_api.application.dto import AnalyzeTranslateResult


@dataclass
class StubAnalyzeService:
    result: AnalyzeTranslateResult | None = None
    error: Exception | None = None
    calls: list[Any] | None = None

    async def analyze_translate(self, command):
        if self.calls is not None:
            self.calls.append(command)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@pytest.fixture
def analyze_result() -> AnalyzeTranslateResult:
    return AnalyzeTranslateResult(
        mode="translation",
        translated_text="こんにちは",
        explanation=None,
        raw_response="こんにちは",
        used_mock=False,
        image_count=1,
        selection_metadata={"url": "https://example.com"},
    )


@pytest.fixture
def stub_analyze_service(analyze_result: AnalyzeTranslateResult) -> StubAnalyzeService:
    return StubAnalyzeService(result=analyze_result, calls=[])


@pytest.fixture
def api_client(stub_analyze_service: StubAnalyzeService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_services] = lambda: BrowserAPIServices(
        analyze_service=stub_analyze_service
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()