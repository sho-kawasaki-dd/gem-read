"""表示言語設定ダイアログの操作を仲介する Presenter。"""

from __future__ import annotations

from dataclasses import replace

from pdf_epub_reader.interfaces.view_interfaces import ILanguageDialogView
from pdf_epub_reader.services.translation_service import TranslationService
from pdf_epub_reader.utils.config import AppConfig, save_config


class LanguagePresenter:
    """ILanguageDialogView と AppConfig の調停役。"""

    def __init__(self, view: ILanguageDialogView, config: AppConfig) -> None:
        self._view = view
        self._config = config
        self._translation_service = TranslationService()

    def show(self) -> AppConfig | None:
        self._view.apply_ui_texts(
            self._translation_service.build_language_dialog_texts(
                self._config.ui_language
            )
        )
        self._populate_view()
        if not self._view.exec_dialog():
            return None

        new_config = replace(
            self._config,
            ui_language=self._view.get_selected_language(),
        )
        save_config(new_config)
        return new_config

    def _populate_view(self) -> None:
        language = self._config.ui_language
        self._view.set_available_languages(
            [
                (
                    "ja",
                    self._translation_service.translate(
                        "dialog.language.option.ja",
                        language,
                    ),
                ),
                (
                    "en",
                    self._translation_service.translate(
                        "dialog.language.option.en",
                        language,
                    ),
                ),
            ]
        )
        self._view.set_selected_language(self._config.ui_language)