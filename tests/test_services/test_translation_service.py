from __future__ import annotations

from pdf_epub_reader.services.translation_service import TranslationService


class TestTranslationService:
    def test_translate_returns_requested_language(self) -> None:
        service = TranslationService()

        assert service.translate("common.not_set", "ja") == "未設定"

    def test_translate_falls_back_to_english_when_key_missing_in_language(self) -> None:
        service = TranslationService(
            translations={
                "en": {"settings.ui_language.label": "Display Language"},
                "ja": {},
            }
        )

        assert (
            service.translate("settings.ui_language.label", "ja")
            == "Display Language"
        )

    def test_translate_normalizes_language_alias_and_formats_text(self) -> None:
        service = TranslationService(
            translations={
                "en": {"status.greeting": "Hello {name}"},
                "ja": {"status.greeting": "こんにちは {name}"},
            }
        )

        assert (
            service.translate("status.greeting", "en-US", name="Alice")
            == "Hello Alice"
        )

    def test_translate_returns_key_when_missing_in_all_languages(self) -> None:
        service = TranslationService()

        assert service.translate("missing.key", "ja") == "missing.key"