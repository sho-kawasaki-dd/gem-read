"""Plotly figure HTML を表示するモードレスウィンドウ。

Phase 1 では `plotly.io.to_html(..., include_plotlyjs="inline")` の出力を
`QWebEngineView` で表示する。HTML が大きくなりやすいため、`setHtml()` では
なく一時ファイルへ書き出して `load()` する方式を採用している。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QSignalBlocker, Qt, QUrl
from PySide6.QtGui import QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pdf_epub_reader.dto import PlotTabPayload


logger = logging.getLogger(__name__)


class PlotWindow(QWidget):
    """Plotly 可視化を独立表示するための軽量ウィンドウ。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.resize(960, 720)
        # WebEngine が読む一時 HTML の寿命をウィンドウに揃える。
        self._temp_dir: TemporaryDirectory[str] | None = None
        self._html_counter = 0
        self._tab_states: list[_PlotTabState] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)

        self._spec_pane = QWidget(self)
        spec_layout = QVBoxLayout(self._spec_pane)
        spec_layout.setContentsMargins(0, 0, 0, 0)
        spec_layout.setSpacing(6)

        self._spec_toggle_button = QToolButton(self._spec_pane)
        self._spec_toggle_button.setCheckable(True)
        self._spec_toggle_button.setChecked(True)
        self._spec_toggle_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self._spec_toggle_button.setArrowType(Qt.ArrowType.LeftArrow)
        self._spec_toggle_button.setText("Specs")
        self._spec_toggle_button.toggled.connect(self._toggle_spec_pane)

        self._spec_list = QListWidget(self._spec_pane)
        self._spec_list.currentRowChanged.connect(self._on_spec_list_row_changed)

        spec_layout.addWidget(self._spec_toggle_button)
        spec_layout.addWidget(self._spec_list)

        self._tab_widget = QTabWidget(self)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)

        self._splitter.addWidget(self._spec_pane)
        self._splitter.addWidget(self._tab_widget)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)

        layout.addWidget(self._splitter)

    def show_figures(self, tab_payloads: list[PlotTabPayload]) -> None:
        """Plotly 可視化タブ群をまとめて表示する。"""
        self._rebuild_tabs(tab_payloads)
        if tab_payloads:
            self._sync_current_index(0)
            self.setWindowTitle(tab_payloads[0].title)
        self.show()
        self.raise_()
        self.activateWindow()

    def show_figure_html(self, html: str, title: str) -> None:
        """後方互換用ラッパ。単一タブ表示として show_figures() に委譲する。"""
        self.show_figures(
            [
                PlotTabPayload(
                    title=title,
                    html=html,
                    spec_source_text="",
                    spec_language="json",
                    spec_index=0,
                )
            ]
        )

    def closeEvent(self, event) -> None:
        """ウィンドウ終了時に一時 HTML を確実に片付ける。"""
        self._cleanup_temp_dir()
        super().closeEvent(event)

    def _rebuild_tabs(self, tab_payloads: list[PlotTabPayload]) -> None:
        self._tab_states.clear()
        self._tab_widget.blockSignals(True)
        self._spec_list.blockSignals(True)
        try:
            self._tab_widget.clear()
            self._spec_list.clear()
            for index, payload in enumerate(tab_payloads):
                tab_state = self._create_tab_state(payload)
                self._tab_states.append(tab_state)
                self._tab_widget.addTab(tab_state.widget, payload.title)
                self._spec_list.addItem(QListWidgetItem(payload.title))
                if index == 0:
                    self._tab_widget.setCurrentIndex(0)
                    self._spec_list.setCurrentRow(0)
        finally:
            self._tab_widget.blockSignals(False)
            self._spec_list.blockSignals(False)

    def _create_tab_state(self, payload: PlotTabPayload) -> _PlotTabState:
        tab_widget = QWidget(self)
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        toolbar = QToolBar(tab_widget)
        toolbar.setMovable(False)
        toolbar.addAction(QAction("Rerender", toolbar))
        toolbar.addAction(QAction("Copy source", toolbar))
        toolbar.addAction(QAction("Copy PNG", toolbar))
        toolbar.addAction(QAction("Save", toolbar))

        web_view = QWebEngineView(tab_widget)
        html_path = self._write_html_file(payload.html)
        web_view.loadFinished.connect(self._on_load_finished)
        web_view.renderProcessTerminated.connect(
            self._on_render_process_terminated
        )
        web_view.load(QUrl.fromLocalFile(str(html_path)))

        tab_layout.addWidget(toolbar)
        tab_layout.addWidget(web_view)
        return _PlotTabState(
            payload=payload,
            widget=tab_widget,
            web_view=web_view,
            html_path=html_path,
        )

    def _sync_current_index(self, index: int) -> None:
        if index < 0 or index >= len(self._tab_states):
            return
        if self._tab_widget.currentIndex() != index:
            self._tab_widget.setCurrentIndex(index)
        if self._spec_list.currentRow() != index:
            self._spec_list.setCurrentRow(index)
        self.setWindowTitle(self._tab_states[index].payload.title)

    def _toggle_spec_pane(self, checked: bool) -> None:
        self._spec_list.setVisible(checked)
        self._spec_pane.setMaximumWidth(16777215 if checked else 56)
        self._spec_toggle_button.setArrowType(
            Qt.ArrowType.LeftArrow if checked else Qt.ArrowType.RightArrow
        )

    def _on_spec_list_row_changed(self, index: int) -> None:
        if index < 0:
            return
        if self._tab_widget.currentIndex() == index:
            self.setWindowTitle(self._tab_states[index].payload.title)
            return
        blocker = QSignalBlocker(self._tab_widget)
        try:
            self._tab_widget.setCurrentIndex(index)
        finally:
            del blocker

    def _on_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        if self._spec_list.currentRow() == index:
            self.setWindowTitle(self._tab_states[index].payload.title)
            return
        blocker = QSignalBlocker(self._spec_list)
        try:
            self._spec_list.setCurrentRow(index)
        finally:
            del blocker
        self.setWindowTitle(self._tab_states[index].payload.title)

    def _write_html_file(self, html: str) -> Path:
        """表示用 HTML を一時ファイルへ書き出し、そのパスを返す。"""
        if self._temp_dir is None:
            self._temp_dir = TemporaryDirectory(prefix="gem_read_plotly_")
        self._html_counter += 1
        html_path = Path(self._temp_dir.name) / f"plot_{self._html_counter:04d}.html"

        html_path.write_text(html, encoding="utf-8")
        return html_path

    def _cleanup_temp_dir(self) -> None:
        """作成済みの一時ディレクトリを破棄して参照をクリアする。"""
        if self._temp_dir is None:
            return
        self._temp_dir.cleanup()
        self._temp_dir = None
        self._tab_states.clear()
        self._html_counter = 0

    def _on_load_finished(self, ok: bool) -> None:
        """WebEngine 読み込み失敗時をログに残す。"""
        if ok:
            return
        logger.warning(
            "PlotWindow failed to load Plotly HTML.",
            extra={"url": self._web_view.url().toString()},
        )

    def _on_render_process_terminated(self, termination_status, exit_code: int) -> None:
        """Chromium renderer 側の異常終了を診断用に記録する。"""
        logger.warning(
            "PlotWindow render process terminated.",
            extra={
                "termination_status": int(termination_status),
                "exit_code": exit_code,
            },
        )


@dataclass
class _PlotTabState:
    payload: PlotTabPayload
    widget: QWidget
    web_view: QWebEngineView
    html_path: Path