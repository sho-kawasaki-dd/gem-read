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

from pdf_epub_reader.dto import LanguageDialogTexts
from pdf_epub_reader.utils.config import DEFAULT_UI_LANGUAGE, normalize_ui_language


class LanguageDialog(QDialog):
    """ILanguageDialogView Protocol を満たす表示言語設定ダイアログ。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        ui_language: str = DEFAULT_UI_LANGUAGE,
    ) -> None:
        super().__init__(parent)
        self._texts: LanguageDialogTexts | None = None

        self.setWindowTitle("")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        self._description_label = QLabel("")
        self._description_label.setWordWrap(True)
        layout.addWidget(self._description_label)

        self._label = QLabel("")
        layout.addWidget(self._label)

        self._language_combo = QComboBox()
        layout.addWidget(self._language_combo)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

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

    def apply_ui_texts(self, texts: LanguageDialogTexts) -> None:
        self._texts = texts
        self.setWindowTitle(texts.window_title)
        self._description_label.setText(texts.description_text)
        self._label.setText(texts.label_text)
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            texts.ok_button_text
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            texts.cancel_button_text
        )