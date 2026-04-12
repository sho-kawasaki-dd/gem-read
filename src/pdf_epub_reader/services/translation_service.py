"""Presenter から利用する UI 翻訳サービス。"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from pdf_epub_reader.resources.i18n import TRANSLATIONS
from pdf_epub_reader.utils.config import DEFAULT_UI_LANGUAGE, UiLanguage, normalize_ui_language

logger = logging.getLogger(__name__)


class TranslationService:
    """階層キーで UI 文言を解決するサービス。"""

    def __init__(
        self,
        translations: Mapping[str, Mapping[str, str]] | None = None,
        default_language: UiLanguage = DEFAULT_UI_LANGUAGE,
    ) -> None:
        source = translations or TRANSLATIONS
        self._translations = {
            language_code: dict(entries)
            for language_code, entries in source.items()
        }
        self._default_language = normalize_ui_language(default_language)

    def translate(self, key: str, language: str, **kwargs: object) -> str:
        """指定言語の翻訳を返し、無ければ英語へフォールバックする。"""
        resolved_language = normalize_ui_language(
            language,
            fallback=self._default_language,
        )
        template = self._lookup(key, resolved_language)
        if template is None and resolved_language != self._default_language:
            template = self._lookup(key, self._default_language)
        if template is None:
            return key
        if not kwargs:
            return template

        try:
            return template.format(**kwargs)
        except (IndexError, KeyError, ValueError) as exc:
            logger.warning(
                "翻訳テンプレートの補間に失敗しました: key=%s, language=%s, error=%s",
                key,
                resolved_language,
                exc,
            )
            return template

    def _lookup(self, key: str, language: UiLanguage) -> str | None:
        entries = self._translations.get(language)
        if entries is None:
            return None
        return entries.get(key)