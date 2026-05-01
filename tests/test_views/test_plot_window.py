from __future__ import annotations

import os
from pathlib import Path
from typing import cast
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from PySide6.QtWidgets import QApplication

from pdf_epub_reader.views.plot_window import PlotWindow


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


def test_show_figure_html_updates_title_and_loads_html() -> None:
    _get_app()
    window = PlotWindow()

    with patch.object(window._web_view, "load") as mock_load:
        window.show_figure_html("<html><body>plot</body></html>", "Plotly Visualization - Demo")

    assert window.windowTitle() == "Plotly Visualization - Demo"
    mock_load.assert_called_once()
    args = mock_load.call_args.args
    loaded_url = args[0]
    assert loaded_url.isLocalFile() is True
    loaded_path = Path(loaded_url.toLocalFile())
    assert loaded_path.name == "plot.html"
    assert loaded_path.read_text(encoding="utf-8") == "<html><body>plot</body></html>"
    assert window.isVisible() is True
    window.close()


def test_close_event_cleans_up_temp_html_directory() -> None:
    _get_app()
    window = PlotWindow()

    with patch.object(window._web_view, "load"):
        window.show_figure_html("<html><body>plot</body></html>", "Plotly Visualization - Demo")

    assert window._html_path is not None
    html_path = window._html_path
    assert html_path.exists() is True

    window.close()

    assert html_path.exists() is False
    assert window._temp_dir is None
    assert window._html_path is None