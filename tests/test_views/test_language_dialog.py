from __future__ import annotations

from tests.mocks.mock_views import MockLanguageDialogView

from pdf_epub_reader.interfaces.view_interfaces import ILanguageDialogView


class TestProtocolConformance:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(MockLanguageDialogView(), ILanguageDialogView)


class TestMockLanguageDialogView:
    def test_setters_and_exec_are_recorded(self) -> None:
        view = MockLanguageDialogView()

        view.set_available_languages([("ja", "日本語"), ("en", "English")])
        view.set_selected_language("en")

        assert view.get_selected_language() == "en"
        assert view.get_calls("set_available_languages") == [
            ([ ("ja", "日本語"), ("en", "English") ],)
        ]
        assert view.exec_dialog() is True