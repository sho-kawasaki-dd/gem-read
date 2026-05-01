"""Plotly figure HTML を表示するモードレスウィンドウ。"""

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget


logger = logging.getLogger(__name__)


class PlotWindow(QWidget):
    """Plotly 可視化を独立表示するための軽量ウィンドウ。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.resize(960, 720)
        self._temp_dir: TemporaryDirectory[str] | None = None
        self._html_path: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._web_view = QWebEngineView(self)
        self._web_view.loadFinished.connect(self._on_load_finished)
        self._web_view.renderProcessTerminated.connect(
            self._on_render_process_terminated
        )
        layout.addWidget(self._web_view)

    def show_figure_html(self, html: str, title: str) -> None:
        """HTML 化済みの Plotly figure をファイル経由で読み込み、前面表示する。"""
        self.setWindowTitle(title)
        html_path = self._write_html_file(html)
        self._web_view.load(QUrl.fromLocalFile(str(html_path)))
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:
        self._cleanup_temp_dir()
        super().closeEvent(event)

    def _write_html_file(self, html: str) -> Path:
        if self._temp_dir is None:
            self._temp_dir = TemporaryDirectory(prefix="gem_read_plotly_")
            self._html_path = Path(self._temp_dir.name) / "plot.html"

        assert self._html_path is not None
        self._html_path.write_text(html, encoding="utf-8")
        return self._html_path

    def _cleanup_temp_dir(self) -> None:
        if self._temp_dir is None:
            return
        self._temp_dir.cleanup()
        self._temp_dir = None
        self._html_path = None

    def _on_load_finished(self, ok: bool) -> None:
        if ok:
            return
        logger.warning(
            "PlotWindow failed to load Plotly HTML.",
            extra={"url": self._web_view.url().toString()},
        )

    def _on_render_process_terminated(self, termination_status, exit_code: int) -> None:
        logger.warning(
            "PlotWindow render process terminated.",
            extra={
                "termination_status": int(termination_status),
                "exit_code": exit_code,
            },
        )