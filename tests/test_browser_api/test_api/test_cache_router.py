from __future__ import annotations

from browser_api.application.dto import CacheListItem, CacheListResult
from browser_api.application.errors import MissingModelError, UnsupportedCacheModelError
from pdf_epub_reader.utils.exceptions import AICacheError, AIKeyMissingError


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


def test_cache_list_returns_browser_extension_caches(api_client, stub_analyze_service) -> None:
    stub_analyze_service.cache_list_result = CacheListResult(
        items=[
            CacheListItem(
                cache_name="cachedContents/be-abc",
                display_name="browser-extension:example.com/article",
                model_name="gemini-2.5-flash",
                expire_time="2026-04-20T10:00:00+00:00",
                token_count=1500,
            ),
            CacheListItem(
                cache_name="cachedContents/be-xyz",
                display_name="browser-extension:example.com/other",
                model_name="gemini-2.5-pro",
                expire_time=None,
                token_count=None,
            ),
        ]
    )

    response = api_client.get("/cache/list")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["items"]) == 2
    assert payload["items"][0]["cache_name"] == "cachedContents/be-abc"
    assert payload["items"][0]["display_name"] == "browser-extension:example.com/article"
    assert payload["items"][0]["model_name"] == "gemini-2.5-flash"
    assert payload["items"][0]["token_count"] == 1500
    assert payload["items"][1]["cache_name"] == "cachedContents/be-xyz"
    assert payload["items"][1]["token_count"] is None


def test_cache_list_returns_empty_items_when_no_caches(api_client, stub_analyze_service) -> None:
    stub_analyze_service.cache_list_result = CacheListResult(items=[])

    response = api_client.get("/cache/list")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["items"] == []


def test_cache_list_returns_500_on_unexpected_error(api_client, stub_analyze_service) -> None:
    stub_analyze_service.cache_list_error = RuntimeError("Upstream exploded")

    response = api_client.get("/cache/list")

    assert response.status_code == 500