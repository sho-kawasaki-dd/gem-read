"""表示言語設定ダイアログの PySide6 実装。"""

from __future__ import annotations

from typing import Literal

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from pdf_epub_reader.services.translation_service import TranslationService
from pdf_epub_reader.utils.config import DEFAULT_UI_LANGUAGE, UiLanguage, normalize_ui_language


class LanguageDialog(QDialog):
    """ILanguageDialogView Protocol を満たす表示言語設定ダイアログ。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        ui_language: str = DEFAULT_UI_LANGUAGE,
    ) -> None:
        super().__init__(parent)
        self._ui_language: UiLanguage = normalize_ui_language(
            ui_language,
            fallback="en",
        )
        self._translation_service = TranslationService()

        self.setWindowTitle(self._translate("dialog.language.title"))
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        self._description_label = QLabel(
            self._translate("dialog.language.description")
        )
        self._description_label.setWordWrap(True)
        layout.addWidget(self._description_label)

        self._label = QLabel(self._translate("dialog.language.label"))
        layout.addWidget(self._label)

        self._language_combo = QComboBox()
        self.set_available_languages(
            [
                ("ja", self._translate("dialog.language.option.ja")),
                ("en", self._translate("dialog.language.option.en")),
            ]
        )
        layout.addWidget(self._language_combo)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            self._translate("common.ok")
        )
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            self._translate("common.cancel")
        )
        layout.addWidget(button_box)

    def get_selected_language(self) -> Literal["ja", "en"]:
        value = self._language_combo.currentData()
        if value == "en":
            return "en"
        return "ja"

    def set_selected_language(self, value: Literal["ja", "en"]) -> None:
        normalized_value = normalize_ui_language(value, fallback="en")
        index = self._language_combo.findData(normalized_value)
        if index >= 0:
            self._language_combo.setCurrentIndex(index)

    def set_available_languages(
        self,
        languages: list[tuple[Literal["ja", "en"], str]],
    ) -> None:
        current_value = self.get_selected_language() if self._language_combo.count() else "ja"
        self._language_combo.clear()
        for language_code, display_name in languages:
            self._language_combo.addItem(display_name, language_code)
        self.set_selected_language(current_value)

    def exec_dialog(self) -> bool:
        return self.exec() == QDialog.DialogCode.Accepted

    def _translate(self, key: str) -> str:
        return self._translation_service.translate(key, self._ui_language)