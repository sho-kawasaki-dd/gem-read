from __future__ import annotations

from browser_api.application.dto import CacheStatusResult
from browser_api.application.errors import MissingModelError, UnsupportedCacheModelError
from pdf_epub_reader.utils.exceptions import AICacheError, AIKeyMissingError


def test_cache_status_returns_active_cache_payload(api_client, stub_analyze_service) -> None:
    response = api_client.get("/cache/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "ok": True,
        "is_active": True,
        "ttl_seconds": 3600,
        "token_count": 2048,
        "cache_name": "cachedContents/abc123",
        "display_name": "example-article",
        "model_name": "gemini-2.5-flash",
        "expire_time": "2026-04-17T10:00:00+00:00",
    }
    assert stub_analyze_service.cache_status_calls == 1


def test_cache_create_returns_created_cache_payload(api_client, stub_analyze_service) -> None:
    response = api_client.post(
        "/cache/create",
        json={
            "full_text": "Long article body",
            "model_name": "gemini-2.5-flash",
            "display_name": "example-article",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_active"] is True
    assert payload["cache_name"] == "cachedContents/abc123"
    assert len(stub_analyze_service.cache_create_calls) == 1
    command = stub_analyze_service.cache_create_calls[0]
    assert command.full_text == "Long article body"
    assert command.model_name == "gemini-2.5-flash"
    assert command.display_name == "example-article"


def test_cache_delete_returns_acknowledgement(api_client, stub_analyze_service) -> None:
    response = api_client.delete("/cache/cachedContents%2Fabc123")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "cache_name": "cachedContents/abc123",
    }
    assert stub_analyze_service.cache_delete_calls == ["cachedContents/abc123"]


def test_cache_status_returns_inactive_payload(api_client, stub_analyze_service) -> None:
    stub_analyze_service.cache_status_result = CacheStatusResult(is_active=False)

    response = api_client.get("/cache/status")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "is_active": False,
        "ttl_seconds": None,
        "token_count": None,
        "cache_name": None,
        "display_name": None,
        "model_name": None,
        "expire_time": None,
    }


def test_cache_create_returns_400_for_missing_model(api_client, stub_analyze_service) -> None:
    stub_analyze_service.cache_create_error = MissingModelError("model_name is required")

    response = api_client.post(
        "/cache/create",
        json={
            "full_text": "Long article body",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "model_name is required"


def test_cache_create_returns_400_for_unsupported_cache_model(api_client, stub_analyze_service) -> None:
    stub_analyze_service.cache_create_error = UnsupportedCacheModelError(
        "This model does not support context cache creation."
    )

    response = api_client.post(
        "/cache/create",
        json={
            "full_text": "Long article body",
            "model_name": "gemini-2.5-flash-lite",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "This model does not support context cache creation."


def test_cache_create_returns_503_for_missing_key(api_client, stub_analyze_service) -> None:
    stub_analyze_service.cache_create_error = AIKeyMissingError("API キーが設定されていません")

    response = api_client.post(
        "/cache/create",
        json={
            "full_text": "Long article body",
            "model_name": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "API キーが設定されていません"


def test_cache_create_maps_upstream_failures_to_502(api_client, stub_analyze_service) -> None:
    stub_analyze_service.cache_create_error = AICacheError("Gemini cache upstream failed")

    response = api_client.post(
        "/cache/create",
        json={
            "full_text": "Long article body",
            "model_name": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Gemini cache upstream failed"