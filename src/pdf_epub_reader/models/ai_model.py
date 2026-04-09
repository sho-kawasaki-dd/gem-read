"""AI 解析 Model のスタブ実装。

Phase 4 で Gemini API ベースの本実装に差し替える。
Phase 2 では GUI の動作確認用に固定のダミー応答を返す。
"""

from __future__ import annotations

from pdf_epub_reader.dto import (
    AnalysisMode,
    AnalysisRequest,
    AnalysisResult,
    CacheStatus,
)


class AIModel:
    """IAIModel のスタブ実装。Phase 4 で Gemini API に差し替える。"""

    async def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """モードに応じて固定のダミー翻訳/応答テキストを返す。"""
        if request.mode == AnalysisMode.TRANSLATION:
            translated = f"[スタブ翻訳] {request.text}"
            explanation = (
                "[スタブ解説] これはスタブの解説テキストです。"
                if request.include_explanation
                else None
            )
            return AnalysisResult(
                translated_text=translated,
                explanation=explanation,
                raw_response=translated,
            )
        else:
            # カスタムプロンプトモード
            response = (
                f"[スタブ応答]\n"
                f"プロンプト: {request.custom_prompt}\n"
                f"対象テキスト: {request.text}"
            )
            return AnalysisResult(raw_response=response)

    async def create_cache(self, full_text: str) -> CacheStatus:
        """キャッシュ作成成功を模した固定レスポンスを返す。"""
        return CacheStatus(
            is_active=True,
            ttl_seconds=3600,
            token_count=len(full_text.split()),
        )

    async def get_cache_status(self) -> CacheStatus:
        """キャッシュ未作成の状態を返す。"""
        return CacheStatus(is_active=False)

    async def invalidate_cache(self) -> None:
        """スタブのため何もしない。"""
        pass

    async def count_tokens(self, text: str) -> int:
        """単語数ベースの簡易トークン数を返す。"""
        return len(text.split())
