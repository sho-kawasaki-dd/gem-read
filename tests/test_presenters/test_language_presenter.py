from __future__ import annotations

from unittest.mock import patch

from tests.mocks.mock_views import MockLanguageDialogView

from pdf_epub_reader.presenters.language_presenter import LanguagePresenter
from pdf_epub_reader.utils.config import AppConfig


class TestLanguagePresenter:
    def test_show_returns_updated_config_and_saves(self) -> None:
        view = MockLanguageDialogView()

        def exec_with_language_change() -> bool:
            view._selected_language = "en"
            return True

        view.exec_dialog = exec_with_language_change  # type: ignore[assignment]
        presenter = LanguagePresenter(view, AppConfig(ui_language="ja"))

        with patch("pdf_epub_reader.presenters.language_presenter.save_config") as mock_save:
            result = presenter.show()

        assert result is not None
        assert result.ui_language == "en"
        mock_save.assert_called_once_with(result)

    def test_cancel_returns_none(self) -> None:
        view = MockLanguageDialogView()
        view._exec_return = False
        presenter = LanguagePresenter(view, AppConfig(ui_language="ja"))

        with patch("pdf_epub_reader.presenters.language_presenter.save_config") as mock_save:
            result = presenter.show()

        assert result is None
        mock_save.assert_not_called()

    def test_populates_available_languages_in_current_language(self) -> None:
        view = MockLanguageDialogView()
        presenter = LanguagePresenter(view, AppConfig(ui_language="en"))

        with patch("pdf_epub_reader.presenters.language_presenter.save_config"):
            presenter.show()

        assert view.get_calls("set_available_languages")[0] == (
            [("ja", "日本語"), ("en", "English")],
        )