from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton, QWidget

from pdf_epub_reader.views.bookmark_panel import BookmarkPanelView
from pdf_epub_reader.views.cache_dialog import CacheDialog
from pdf_epub_reader.views.language_dialog import LanguageDialog
from pdf_epub_reader.views.main_window import MainWindow
from pdf_epub_reader.views.settings_dialog import SettingsDialog
from pdf_epub_reader.views.side_panel_view import SidePanelView


_APP = QApplication.instance() or QApplication([])


def _button_texts(widget: QWidget) -> set[str]:
    return {button.text() for button in widget.findChildren(QPushButton)}


def _checkbox_texts(widget: QWidget) -> set[str]:
    return {checkbox.text() for checkbox in widget.findChildren(QCheckBox)}


class TestSettingsDialogTranslations:
    def test_english_static_strings_are_translated(self) -> None:
        dialog = SettingsDialog(ui_language="en")

        assert dialog.windowTitle() == "Preferences"
        assert dialog._tabs.tabText(0) == "Rendering"
        assert dialog._tabs.tabText(1) == "Detection"
        assert dialog._tabs.tabText(2) == "AI Models"
        assert "Fetch Models" in _button_texts(dialog)
        assert "Reset to Defaults" in _button_texts(dialog)
        assert "High-quality downscale (Lanczos)" in _checkbox_texts(dialog)

        dialog.set_fetch_models_loading(True)

        assert dialog._fetch_status_label.text() == "Fetching..."
        dialog.close()


class TestCacheDialogTranslations:
    def test_english_static_strings_are_translated(self) -> None:
        dialog = CacheDialog(ui_language="en")

        assert dialog.windowTitle() == "Cache Management"
        assert dialog._tabs.tabText(0) == "Current Cache"
        assert dialog._tabs.tabText(1) == "Cache Browser"
        assert "Update TTL" in _button_texts(dialog)
        assert "Delete Selected" in _button_texts(dialog)
        assert "Close" in _button_texts(dialog)
        headers = [dialog._table.horizontalHeaderItem(i).text() for i in range(5)]
        assert headers == ["Name", "Model", "Display Name", "Tokens", "Expire"]

        dialog.set_cache_ttl_seconds(125)
        dialog.set_cache_is_active(True)
        assert dialog._ttl_label.text() == "2 min 5 sec"
        assert dialog._active_label.text() == "Active"

        dialog.set_cache_is_active(False)
        assert dialog._active_label.text() == "Inactive"
        dialog.close()


class TestLanguageDialogTranslations:
    def test_english_strings_are_translated(self) -> None:
        dialog = LanguageDialog(ui_language="en")

        assert dialog.windowTitle() == "Language"
        assert dialog._description_label.text() == (
            "Choose the language used in the interface."
        )
        assert dialog._label.text() == "Display Language:"
        assert dialog._language_combo.itemText(0) == "日本語"
        assert dialog._language_combo.itemText(1) == "English"
        assert "OK" in _button_texts(dialog)
        assert "Cancel" in _button_texts(dialog)

        dialog.set_selected_language("en")

        assert dialog.get_selected_language() == "en"
        dialog.close()


class TestBookmarkPanelTranslations:
    def test_header_updates_with_language_change(self) -> None:
        panel = BookmarkPanelView(ui_language="en")

        assert panel._tree.headerItem().text(0) == "Bookmarks"

        panel.apply_ui_language("ja")

        assert panel._tree.headerItem().text(0) == "しおり"
        panel.close()


class TestMainWindowTranslations:
    def test_language_application_updates_menu_status_and_overlay(self) -> None:
        bookmark_panel = BookmarkPanelView(ui_language="en")
        side_panel = QWidget()
        window = MainWindow(
            side_panel=side_panel,
            bookmark_panel=bookmark_panel,
            ui_language="en",
        )

        assert window.windowTitle() == "PDF/EPUB Reader"
        assert window._file_menu.title() == "&File"
        assert window._status_label.text() == "Ready"
        assert bookmark_panel._tree.headerItem().text(0) == "Bookmarks"
        assert window._overlay._page_label.text() == "Page:"

        window.apply_ui_language("ja")

        assert window._file_menu.title() == "ファイル(&F)"
        assert window._status_label.text() == "準備完了"
        assert bookmark_panel._tree.headerItem().text(0) == "しおり"
        assert window._overlay._page_label.text() == "ページ:"
        window.close()
        bookmark_panel.close()
        side_panel.close()


class TestSidePanelTranslations:
    def test_language_application_updates_static_strings(self) -> None:
        panel = SidePanelView(ui_language="en")

        assert panel._selection_section._toggle_btn.text().endswith("Selections")
        assert panel._selection_summary_label.text() == "Selections 0"
        assert panel._translate_btn.text() == "Translate"
        assert panel._explain_btn.text() == "Translate with Explanation"
        assert panel._submit_btn.text() == "Submit"
        assert panel._tab_widget.tabText(0) == "Translation"
        assert panel._tab_widget.tabText(1) == "Custom Prompt"
        assert panel._cache_label.text() == "Cache Status: ---"

        panel.apply_ui_language("ja")

        assert panel._selection_section._toggle_btn.text().endswith("選択一覧")
        assert panel._selection_summary_label.text() == "選択 0 件"
        assert panel._translate_btn.text() == "翻訳"
        assert panel._explain_btn.text() == "解説付き翻訳"
        assert panel._submit_btn.text() == "送信"
        assert panel._tab_widget.tabText(0) == "翻訳"
        assert panel._tab_widget.tabText(1) == "カスタムプロンプト"
        assert panel._cache_label.text() == "キャッシュステータス: ---"
        panel.close()