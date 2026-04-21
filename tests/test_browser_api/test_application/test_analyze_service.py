from __future__ import annotations

import base64
from dataclasses import dataclass

import pytest

from browser_api.application.dto import AnalyzeTranslateCommand
from browser_api.application.dto import CacheCreateCommand, TokenCountCommand
from browser_api.application.errors import (
    InvalidImagePayloadError,
    MissingModelError,
    UnsupportedCacheModelError,
)
from browser_api.application.services.analyze_service import AnalyzeService
from pdf_epub_reader.dto import AnalysisResult, AnalysisUsage, CacheStatus, ModelInfo
from pdf_epub_reader.utils.config import AppConfig
from pdf_epub_reader.utils.exceptions import AICacheError, AIAPIError, AIKeyMissingError


@dataclass
class StubAIGateway:
    """Gateway stub for service tests so AnalyzeService behavior is verified without live Gemini calls."""

    result: AnalysisResult | None = None
    models_result: list[ModelInfo] | None = None
    error: Exception | None = None
    model_error: Exception | None = None
    token_result: int | None = None
    token_error: Exception | None = None
    cache_result: CacheStatus | None = None
    cache_create_error: Exception | None = None
    cache_status_error: Exception | None = None
    delete_cache_error: Exception | None = None
    requests: list[object] | None = None
    model_calls: int = 0
    token_calls: list[object] | None = None
    cache_create_calls: list[object] | None = None
    cache_status_calls: int = 0
    delete_cache_calls: list[str] | None = None

    async def analyze(self, request):
        if self.requests is not None:
            self.requests.append(request)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result

    async def list_available_models(self):
        self.model_calls += 1
        if self.model_error is not None:
            raise self.model_error
        assert self.models_result is not None
        return self.models_result

    async def count_tokens(self, text: str, *, model_name: str | None = None):
        if self.token_calls is not None:
            self.token_calls.append({"text": text, "model_name": model_name})
        if self.token_error is not None:
            raise self.token_error
        assert self.token_result is not None
        return self.token_result

    async def create_cache(
        self,
        full_text: str,
        *,
        model_name: str | None = None,
        display_name: str | None = None,
    ):
        if self.cache_create_calls is not None:
            self.cache_create_calls.append(
                {
                    "full_text": full_text,
                    "model_name": model_name,
                    "display_name": display_name,
                }
            )
        if self.cache_create_error is not None:
            raise self.cache_create_error
        assert self.cache_result is not None
        return self.cache_result

    async def get_cache_status(self):
        self.cache_status_calls += 1
        if self.cache_status_error is not None:
            raise self.cache_status_error
        assert self.cache_result is not None
        return self.cache_result

    async def delete_cache(self, cache_name: str):
        if self.delete_cache_calls is not None:
            self.delete_cache_calls.append(cache_name)
        if self.delete_cache_error is not None:
            raise self.delete_cache_error


def _build_command(
    *,
    mode: str = "translation",
    model_name: str | None = None,
    cache_name: str | None = None,
    images: list[str] | None = None,
    custom_prompt: str | None = None,
    text: str = "Selected text",
):
    return AnalyzeTranslateCommand(
        text=text,
        model_name=model_name,
        images=images or [],
        mode=mode,
        cache_name=cache_name,
        custom_prompt=custom_prompt,
        selection_metadata={"url": "https://example.com/article"},
    )


class TestAnalyzeService:
    """Verify service-only behavior such as fallback rules, request mapping, and image decoding."""

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
        assert result.usage is None
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
                usage=AnalysisUsage(
                    prompt_token_count=42,
                    cached_content_token_count=1600,
                    candidates_token_count=73,
                    total_token_count=1715,
                ),
                cache_request_attempted=True,
                cache_request_failed=True,
                cache_fallback_reason="permission-denied",
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
        assert result.usage is not None
        assert result.usage.cached_content_token_count == 1600
        assert result.cache_request_attempted is True
        assert result.cache_request_failed is True
        assert result.cache_fallback_reason == "permission-denied"
        assert gateway.requests[0].include_explanation is True

    @pytest.mark.asyncio
    async def test_custom_prompt_uses_custom_mode_and_prompt(self) -> None:
        gateway = StubAIGateway(
            result=AnalysisResult(raw_response="custom answer"),
            requests=[],
        )
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.analyze_translate(
            _build_command(mode="custom_prompt", custom_prompt="Summarize this")
        )

        assert result.mode == "custom_prompt"
        assert result.translated_text == "custom answer"
        assert result.raw_response == "custom answer"
        request = gateway.requests[0]
        assert request.mode.value == "custom_prompt"
        assert request.custom_prompt == "Summarize this"

    @pytest.mark.asyncio
    async def test_forwards_explicit_cache_name_to_ai_request(self) -> None:
        gateway = StubAIGateway(
            result=AnalysisResult(raw_response="cached answer"),
            requests=[],
        )
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        await service.analyze_translate(
            _build_command(
                model_name="gemini-2.5-flash",
                cache_name="cachedContents/article-1",
            )
        )

        request = gateway.requests[0]
        assert request.model_name == "gemini-2.5-flash"
        assert request.cache_name == "cachedContents/article-1"

    @pytest.mark.asyncio
    async def test_accepts_image_only_requests_without_mutating_empty_text(self) -> None:
        image_bytes = b"image-payload"
        image_payload = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
        gateway = StubAIGateway(
            result=AnalysisResult(raw_response="image answer"),
            requests=[],
        )
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.analyze_translate(
            _build_command(text="", images=[image_payload])
        )

        assert result.raw_response == "image answer"
        request = gateway.requests[0]
        assert request.text == ""
        assert request.images == [image_bytes]

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
    async def test_custom_prompt_mock_response_contains_prompt(self) -> None:
        gateway = StubAIGateway(error=AIKeyMissingError("missing key"), requests=[])
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.analyze_translate(
            _build_command(mode="custom_prompt", custom_prompt="Summarize")
        )

        assert result.used_mock is True
        assert result.availability == "mock"
        assert result.degraded_reason == "mock-response"
        assert "Prompt: Summarize" in result.raw_response

    @pytest.mark.asyncio
    async def test_image_only_mock_response_uses_placeholder_text(self) -> None:
        gateway = StubAIGateway(error=AIKeyMissingError("missing key"), requests=[])
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.analyze_translate(_build_command(text="", images=["abc="]))

        assert result.used_mock is True
        assert "[image-only selection]" in result.raw_response

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

    @pytest.mark.asyncio
    async def test_list_models_returns_live_results_when_gateway_succeeds(self) -> None:
        gateway = StubAIGateway(
            models_result=[
                ModelInfo(model_id="gemini-2.5-pro", display_name="Gemini 2.5 Pro"),
            ]
        )
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.list_models()

        assert result.source == "live"
        assert result.availability == "live"
        assert result.models[0].model_id == "gemini-2.5-pro"

    @pytest.mark.asyncio
    async def test_list_models_falls_back_to_config_when_api_key_is_missing(self) -> None:
        gateway = StubAIGateway(model_error=AIKeyMissingError("missing key"))
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(
                gemini_model_name="gemini-2.5-flash",
                selected_models=["gemini-2.5-flash", "gemini-2.5-pro"],
            ),
        )

        result = await service.list_models()

        assert result.source == "config_fallback"
        assert result.availability == "degraded"
        assert result.degraded_reason == "mock-response"
        assert [model.model_id for model in result.models] == [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ]

    @pytest.mark.asyncio
    async def test_list_models_falls_back_to_config_when_upstream_errors(self) -> None:
        gateway = StubAIGateway(model_error=AIAPIError("upstream down", status_code=503))
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(
                gemini_model_name="gemini-2.5-flash",
                selected_models=["gemini-2.5-pro"],
            ),
        )

        result = await service.list_models()

        assert result.source == "config_fallback"
        assert result.availability == "degraded"
        assert result.degraded_reason == "config-fallback"
        assert "upstream down" in (result.detail or "")

    @pytest.mark.asyncio
    async def test_count_tokens_uses_requested_model(self) -> None:
        gateway = StubAIGateway(token_result=321, token_calls=[])
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.count_tokens(
            TokenCountCommand(text="Article body", model_name="gemini-2.5-flash")
        )

        assert result.token_count == 321
        assert result.model_name == "gemini-2.5-flash"
        assert gateway.token_calls == [
            {"text": "Article body", "model_name": "gemini-2.5-flash"}
        ]

    @pytest.mark.asyncio
    async def test_create_cache_returns_normalized_status(self) -> None:
        gateway = StubAIGateway(
            cache_result=CacheStatus(
                is_active=True,
                ttl_seconds=3600,
                token_count=2048,
                cache_name="cachedContents/abc123",
                display_name="example-article",
                model_name="gemini-2.5-flash",
                expire_time="2026-04-17T10:00:00+00:00",
            ),
            cache_create_calls=[],
        )
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.create_cache(
            CacheCreateCommand(
                full_text="Long article body",
                model_name="gemini-2.5-flash",
                display_name="example-article",
            )
        )

        assert result.is_active is True
        assert result.cache_name == "cachedContents/abc123"
        assert gateway.cache_create_calls == [
            {
                "full_text": "Long article body",
                "model_name": "gemini-2.5-flash",
                "display_name": "example-article",
            }
        ]

    @pytest.mark.asyncio
    async def test_delete_cache_returns_acknowledgement(self) -> None:
        gateway = StubAIGateway(delete_cache_calls=[])
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        result = await service.delete_cache("cachedContents/abc123")

        assert result.cache_name == "cachedContents/abc123"
        assert gateway.delete_cache_calls == ["cachedContents/abc123"]

    @pytest.mark.asyncio
    async def test_create_cache_raises_unsupported_cache_model_for_supported_error_text(self) -> None:
        gateway = StubAIGateway(
            cache_create_error=AICacheError(
                "このモデルはコンテキストキャッシュをサポートしていません: gemini-2.5-flash-lite"
            )
        )
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        with pytest.raises(UnsupportedCacheModelError):
            await service.create_cache(
                CacheCreateCommand(
                    full_text="Long article body",
                    model_name="gemini-2.5-flash-lite",
                )
            )

    @pytest.mark.asyncio
    async def test_create_cache_propagates_generic_cache_errors(self) -> None:
        gateway = StubAIGateway(cache_create_error=AICacheError("Gemini cache upstream failed"))
        service = AnalyzeService(
            ai_gateway=gateway,
            config=AppConfig(gemini_model_name="default-model"),
        )

        with pytest.raises(AICacheError):
            await service.create_cache(
                CacheCreateCommand(
                    full_text="Long article body",
                    model_name="gemini-2.5-flash",
                )
            )