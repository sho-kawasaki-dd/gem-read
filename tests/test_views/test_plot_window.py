from __future__ import annotations

import os
from pathlib import Path
from typing import cast
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pdf_epub_reader.dto import PlotTabPayload
from pdf_epub_reader.views.plot_window import PlotWindow


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


def test_show_figures_builds_splitter_tabs_and_syncs_selection() -> None:
    _get_app()
    window = PlotWindow()

    with patch("pdf_epub_reader.views.plot_window.QWebEngineView.load") as mock_load:
        window.show_figures(
            [
                PlotTabPayload(
                    title="Plotly Visualization - Demo",
                    html="<html><body>plot</body></html>",
                    spec_source_text='{"data": []}',
                    spec_language="json",
                    spec_index=0,
                )
            ]
        )

    assert window.windowTitle() == "Plotly Visualization - Demo"
    assert window._splitter.orientation() == Qt.Orientation.Horizontal
    assert window._spec_list.count() == 1
    assert window._tab_widget.count() == 1
    assert window._spec_list.currentRow() == 0
    assert window._tab_widget.currentIndex() == 0
    mock_load.assert_called_once()
    loaded_url = mock_load.call_args.args[0]
    assert loaded_url.isLocalFile() is True
    loaded_path = Path(loaded_url.toLocalFile())
    assert loaded_path.name == "plot_0001.html"
    assert loaded_path.read_text(encoding="utf-8") == "<html><body>plot</body></html>"
    assert window.isVisible() is True
    window.close()


def test_selection_sync_keeps_list_and_tabs_aligned() -> None:
    _get_app()
    window = PlotWindow()

    with patch("pdf_epub_reader.views.plot_window.QWebEngineView.load"):
        window.show_figures(
            [
                PlotTabPayload(
                    title="Plot A",
                    html="<html><body>plot</body></html>",
                    spec_source_text="{}",
                    spec_language="json",
                    spec_index=0,
                ),
                PlotTabPayload(
                    title="Plot B",
                    html="<html><body>plot2</body></html>",
                    spec_source_text="{}",
                    spec_language="json",
                    spec_index=1,
                ),
            ]
        )

    window._spec_list.setCurrentRow(1)
    assert window._tab_widget.currentIndex() == 1

    window._tab_widget.setCurrentIndex(0)
    assert window._spec_list.currentRow() == 0


def test_close_event_cleans_up_temp_html_directory() -> None:
    _get_app()
    window = PlotWindow()

    with patch("pdf_epub_reader.views.plot_window.QWebEngineView.load"):
        window.show_figures(
            [
                PlotTabPayload(
                    title="Plotly Visualization - Demo",
                    html="<html><body>plot</body></html>",
                    spec_source_text='{"data": []}',
                    spec_language="json",
                    spec_index=0,
                )
            ]
        )

    assert window._tab_states[0].html_path.exists() is True
    html_path = window._tab_states[0].html_path
    window.close()

    assert html_path.exists() is False
    assert window._temp_dir is None
    assert window._tab_states == []