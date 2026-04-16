from __future__ import annotations

from pdf_epub_reader.dto import AnalysisRequest, AnalysisResult, ModelInfo
from pdf_epub_reader.models.ai_model import AIModel


class GemReadAIGateway:
    def __init__(self, ai_model: AIModel) -> None:
        self._ai_model = ai_model

    async def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        return await self._ai_model.analyze(request)

    async def list_available_models(self) -> list[ModelInfo]:
        return await self._ai_model.list_available_models()