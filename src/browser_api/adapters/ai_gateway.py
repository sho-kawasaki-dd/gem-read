from __future__ import annotations

from pdf_epub_reader.dto import AnalysisRequest, AnalysisResult, ModelInfo
from pdf_epub_reader.models.ai_model import AIModel


class GemReadAIGateway:
    """Bridge browser_api use cases to the existing pdf_epub_reader AIModel.

    adapter に依存点を閉じ込めることで、router や service が legacy 実装詳細を知らずに済む。
    """

    def __init__(self, ai_model: AIModel) -> None:
        self._ai_model = ai_model

    async def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        return await self._ai_model.analyze(request)

    async def list_available_models(self) -> list[ModelInfo]:
        return await self._ai_model.list_available_models()

    async def count_tokens(self, text: str, *, model_name: str | None = None) -> int:
        return await self._ai_model.count_tokens(text, model_name=model_name)

    async def create_cache(
        self,
        full_text: str,
        *,
        model_name: str | None = None,
        display_name: str | None = None,
    ) -> CacheStatus:
        return await self._ai_model.create_cache(
            full_text,
            model_name=model_name,
            display_name=display_name,
        )

    async def delete_cache(self, cache_name: str) -> None:
        await self._ai_model.delete_cache(cache_name)