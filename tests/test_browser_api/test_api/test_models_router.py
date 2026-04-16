from __future__ import annotations

from browser_api.application.dto import ModelCatalogResult
from pdf_epub_reader.dto import ModelInfo


# popup 向け model catalog が degraded metadata を保ったまま返ることを固定する suite。
def test_models_returns_live_payload(api_client, stub_analyze_service) -> None:
    response = api_client.get("/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "ok": True,
        "models": [
            {
                "model_id": "gemini-2.5-flash",
                "display_name": "Gemini 2.5 Flash",
            }
        ],
        "source": "live",
        "availability": "live",
        "detail": None,
        "degraded_reason": None,
    }
    assert stub_analyze_service.model_calls == 1


def test_models_returns_config_fallback_payload(api_client, stub_analyze_service) -> None:
    stub_analyze_service.models_result = ModelCatalogResult(
        models=[ModelInfo(model_id="gemini-2.5-pro", display_name="gemini-2.5-pro")],
        source="config_fallback",
        availability="degraded",
        detail="Configured models only.",
        degraded_reason="mock-response",
    )

    response = api_client.get("/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "config_fallback"
    assert payload["availability"] == "degraded"
    assert payload["detail"] == "Configured models only."
    assert payload["degraded_reason"] == "mock-response"