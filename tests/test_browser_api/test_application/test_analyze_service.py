from __future__ import annotations

import base64
from dataclasses import dataclass

import pytest

from browser_api.application.dto import AnalyzeTranslateCommand
from browser_api.application.errors import InvalidImagePayloadError, MissingModelError
from browser_api.application.services.analyze_service import AnalyzeService
from pdf_epub_reader.dto import AnalysisResult
from pdf_epub_reader.utils.config import AppConfig
from pdf_epub_reader.utils.exceptions import AIKeyMissingError


@dataclass
class StubAIGateway:
    result: AnalysisResult | None = None
    error: Exception | None = None
    requests: list[object] | None = None

    async def analyze(self, request):
        if self.requests is not None:
            self.requests.append(request)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def _build_command(
    *,
    mode: str = "translation",
    model_name: str | None = None,
    images: list[str] | None = None,
):
    return AnalyzeTranslateCommand(
        text="Selected text",
        model_name=model_name,
        images=images or [],
        mode=mode,
        selection_metadata={"url": "https://example.com/article"},
    )


class TestAnalyzeService:
    @pytest.mark.asyncio
    async def test_uses_requested_model_and_decodes_images(self) -> None:
        image_bytes = b"image-payload"
        image_payload = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
        gateway = StubAIGateway(
            result=AnalysisResult(translated_text="翻訳結果", raw_response="翻訳結果"),
            requests=[],
        )
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.analyze_translate(
            _build_command(model_name="gemini-2.5-flash", images=[image_payload])
        )

        assert result.mode == "translation"
        assert result.translated_text == "翻訳結果"
        assert result.used_mock is False
        assert result.image_count == 1
        request = gateway.requests[0]
        assert request.text == "Selected text"
        assert request.model_name == "gemini-2.5-flash"
        assert request.include_explanation is False
        assert request.images == [image_bytes]

    @pytest.mark.asyncio
    async def test_translation_with_explanation_preserves_explanation_fields(self) -> None:
        gateway = StubAIGateway(
            result=AnalysisResult(
                translated_text="翻訳本文",
                explanation="補足説明",
                raw_response="翻訳本文\n\n---\n\n補足説明",
            ),
            requests=[],
        )
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.analyze_translate(
            _build_command(mode="translation_with_explanation")
        )

        assert result.mode == "translation_with_explanation"
        assert result.translated_text == "翻訳本文"
        assert result.explanation == "補足説明"
        assert result.raw_response == "翻訳本文\n\n---\n\n補足説明"
        assert gateway.requests[0].include_explanation is True

    @pytest.mark.asyncio
    async def test_falls_back_to_mock_when_api_key_is_missing(self) -> None:
        gateway = StubAIGateway(error=AIKeyMissingError("missing key"), requests=[])
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.analyze_translate(
            _build_command(mode="translation_with_explanation")
        )

        assert result.used_mock is True
        assert result.translated_text.startswith("[mock: explanation]")
        assert result.explanation is not None
        assert "Mock explanation" in result.raw_response
        assert result.selection_metadata == {"url": "https://example.com/article"}

    @pytest.mark.asyncio
    async def test_raises_missing_model_when_request_and_config_are_empty(self) -> None:
        gateway = StubAIGateway(result=AnalysisResult(raw_response="unused"))
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name=" "),
        )

        with pytest.raises(MissingModelError):
            await service.analyze_translate(_build_command())

    @pytest.mark.asyncio
    async def test_raises_invalid_image_payload_for_non_base64_data(self) -> None:
        gateway = StubAIGateway(result=AnalysisResult(raw_response="unused"))
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        with pytest.raises(InvalidImagePayloadError):
            await service.analyze_translate(
                _build_command(images=["data:image/png;base64,not-base64!!!"])
            )