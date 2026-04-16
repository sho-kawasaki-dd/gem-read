from __future__ import annotations

from browser_api.application.dto import AnalyzeTranslateResult
from pdf_epub_reader.utils.exceptions import AIAPIError


def test_translate_returns_response_payload(api_client, stub_analyze_service) -> None:
    response = api_client.post(
        "/analyze/translate",
        json={
            "text": "Hello",
            "images": ["data:image/png;base64,QUJD"],
            "mode": "translation",
            "selection_metadata": {
                "url": "https://example.com",
                "page_title": "Example",
                "viewport_width": 1440,
                "viewport_height": 900,
                "device_pixel_ratio": 2,
                "rect": {
                    "left": 10,
                    "top": 20,
                    "width": 30,
                    "height": 40,
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["translated_text"] == "こんにちは"
    assert payload["selection_metadata"]["url"] == "https://example.com"
    assert len(stub_analyze_service.calls) == 1
    command = stub_analyze_service.calls[0]
    assert command.text == "Hello"
    assert command.images == ["data:image/png;base64,QUJD"]
    assert command.selection_metadata["page_title"] == "Example"


def test_translate_returns_400_for_missing_model(api_client, stub_analyze_service) -> None:
    stub_analyze_service.error = ValueError("placeholder")
    from browser_api.application.errors import MissingModelError

    stub_analyze_service.error = MissingModelError("model_name is required")

    response = api_client.post(
        "/analyze/translate",
        json={
            "text": "Hello",
            "images": [],
            "mode": "translation",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "model_name is required"


def test_translate_maps_ai_errors_to_http_status(api_client, stub_analyze_service) -> None:
    stub_analyze_service.error = AIAPIError("Gemini upstream failed", status_code=503)

    response = api_client.post(
        "/analyze/translate",
        json={
            "text": "Hello",
            "images": [],
            "mode": "translation",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Gemini upstream failed"


def test_translate_rejects_empty_text(api_client, stub_analyze_service) -> None:
    stub_analyze_service.result = AnalyzeTranslateResult(
        mode="translation",
        translated_text="unused",
        explanation=None,
        raw_response="unused",
        used_mock=False,
        image_count=0,
        selection_metadata=None,
    )

    response = api_client.post(
        "/analyze/translate",
        json={
            "text": "",
            "images": [],
            "mode": "translation",
        },
    )

    assert response.status_code == 422