from __future__ import annotations

from browser_api.application.errors import MissingModelError
from pdf_epub_reader.utils.exceptions import AIAPIError, AIKeyMissingError


def test_tokens_count_returns_estimate(api_client, stub_analyze_service) -> None:
    response = api_client.post(
        "/tokens/count",
        json={
            "text": "Article body for estimation",
            "model_name": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "token_count": 321,
        "model_name": "gemini-2.5-flash",
    }
    assert len(stub_analyze_service.token_calls) == 1
    command = stub_analyze_service.token_calls[0]
    assert command.text == "Article body for estimation"
    assert command.model_name == "gemini-2.5-flash"


def test_tokens_count_returns_400_for_missing_model(api_client, stub_analyze_service) -> None:
    stub_analyze_service.token_error = MissingModelError("model_name is required")

    response = api_client.post(
        "/tokens/count",
        json={
            "text": "Article body for estimation",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "model_name is required"


def test_tokens_count_returns_503_for_missing_key(api_client, stub_analyze_service) -> None:
    stub_analyze_service.token_error = AIKeyMissingError("API キーが設定されていません")

    response = api_client.post(
        "/tokens/count",
        json={
            "text": "Article body for estimation",
            "model_name": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "API キーが設定されていません"


def test_tokens_count_maps_upstream_failures(api_client, stub_analyze_service) -> None:
    stub_analyze_service.token_error = AIAPIError("Gemini token endpoint failed", status_code=503)

    response = api_client.post(
        "/tokens/count",
        json={
            "text": "Article body for estimation",
            "model_name": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Gemini token endpoint failed"