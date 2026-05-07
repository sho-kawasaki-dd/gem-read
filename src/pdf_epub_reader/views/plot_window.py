"""Plotly figure HTML を表示するモードレスウィンドウ。

Phase 1 では `plotly.io.to_html(..., include_plotlyjs="inline")` の出力を
`QWebEngineView` で表示する。HTML が大きくなりやすいため、`setHtml()` では
なく一時ファイルへ書き出して `load()` する方式を採用している。
"""

from __future__ import annotations

from datetime import datetime
import logging
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from collections.abc import Callable

from PySide6.QtCore import QSignalBlocker, Qt, QUrl
from PySide6.QtGui import QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pdf_epub_reader.dto import PlotTabPayload, PlotWindowTexts


logger = logging.getLogger(__name__)


_DEFAULT_TEXTS = PlotWindowTexts(
    spec_list_pane_title="Specs",
    toolbar_rerender="Rerender",
    toolbar_copy_source="Copy source",
    toolbar_copy_png="Copy PNG",
    toolbar_save="Save",
    kaleido_unavailable_tooltip="PNG export is unavailable until kaleido is installed.",
    rerender_failed_status="Failed to rerender the Plotly figure: {details}",
    copy_png_failed_status="Failed to copy the Plotly figure as PNG: {details}",
    tab_title_template="{title}",
)


class PlotWindow(QWidget):
    """Plotly 可視化を独立表示するための軽量ウィンドウ。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        texts: PlotWindowTexts | None = None,
        export_folder: str = "",
    ) -> None:
        super().__init__(parent)
        self.resize(960, 720)
        self._texts = texts or _DEFAULT_TEXTS
        self._export_folder = export_folder.strip()
        # WebEngine が読む一時 HTML の寿命をウィンドウに揃える。
        self._temp_dir: TemporaryDirectory[str] | None = None
        self._html_counter = 0
        self._tab_states: list[_PlotTabState] = []
        self._on_rerender_requested: Callable[[PlotTabPayload], None] | None = None
        self._on_save_requested: Callable[[PlotTabPayload, Path], None] | None = None
        self._kaleido_available = True

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
        self._spec_toggle_button.setText(self._texts.spec_list_pane_title)
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

    def set_on_rerender_requested(
        self, cb: Callable[[PlotTabPayload], None]
    ) -> None:
        """現在のタブを再描画したいときに呼ぶコールバックを登録する。"""
        self._on_rerender_requested = cb

    def set_on_save_requested(
        self, cb: Callable[[PlotTabPayload, Path], None]
    ) -> None:
        """保存先が決まったときに呼ぶコールバックを登録する。"""
        self._on_save_requested = cb

    def set_kaleido_available(self, available: bool) -> None:
        """PNG コピーや PNG/SVG 保存の可用性を反映する。"""
        self._kaleido_available = available
        for tab_state in self._tab_states:
            tab_state.copy_png_action.setEnabled(available)
            if available:
                tab_state.copy_png_action.setToolTip("")
            else:
                tab_state.copy_png_action.setToolTip(
                    self._texts.kaleido_unavailable_tooltip
                )

    def reload_tab(self, index: int, payload: PlotTabPayload) -> None:
        """既存タブの内容を新しい HTML で差し替える。"""
        if index < 0 or index >= len(self._tab_states):
            return

        tab_state = self._tab_states[index]
        tab_state.payload = payload
        tab_state.html_path = self._write_html_file(payload.html)
        tab_state.web_view.load(QUrl.fromLocalFile(str(tab_state.html_path)))
        formatted_title = self._format_tab_title(payload)
        self._tab_widget.setTabText(index, formatted_title)
        item = self._spec_list.item(index)
        if item is not None:
            item.setText(formatted_title)
        if self._tab_widget.currentIndex() == index:
            self.setWindowTitle(payload.title)

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
                formatted_title = self._format_tab_title(payload)
                self._tab_widget.addTab(tab_state.widget, formatted_title)
                self._spec_list.addItem(QListWidgetItem(formatted_title))
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
        rerender_action = QAction(self._texts.toolbar_rerender, toolbar)
        rerender_action.triggered.connect(lambda: self._request_rerender(payload))
        copy_source_action = QAction(self._texts.toolbar_copy_source, toolbar)
        copy_source_action.triggered.connect(
            lambda: self._copy_source_to_clipboard(payload)
        )
        copy_png_action = QAction(self._texts.toolbar_copy_png, toolbar)
        copy_png_action.triggered.connect(
            lambda: self._copy_png_to_clipboard(tab_widget)
        )
        save_action = QAction(self._texts.toolbar_save, toolbar)
        save_action.triggered.connect(lambda: self._request_save(payload))
        save_action.setToolTip(self._texts.kaleido_unavailable_tooltip)
        copy_png_action.setEnabled(self._kaleido_available)
        if not self._kaleido_available:
            copy_png_action.setToolTip(self._texts.kaleido_unavailable_tooltip)
        toolbar.addAction(rerender_action)
        toolbar.addAction(copy_source_action)
        toolbar.addAction(copy_png_action)
        toolbar.addAction(save_action)

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
            toolbar=toolbar,
            rerender_action=rerender_action,
            copy_source_action=copy_source_action,
            copy_png_action=copy_png_action,
            save_action=save_action,
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

    def _request_rerender(self, payload: PlotTabPayload) -> None:
        if self._on_rerender_requested is None:
            return
        self._on_rerender_requested(payload)

    def _request_save(self, payload: PlotTabPayload) -> None:
        initial_path = self._build_save_initial_path(payload)
        filters = self._build_save_filters()
        selected_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            self._texts.toolbar_save,
            str(initial_path),
            filters,
        )
        if not selected_path:
            return

        target_path = Path(selected_path)
        if target_path.suffix == "":
            suffix = self._infer_suffix_from_filter(selected_filter)
            if suffix:
                target_path = target_path.with_suffix(f".{suffix}")

        if self._on_save_requested is None:
            return
        self._on_save_requested(payload, target_path)

    def _build_save_initial_path(self, payload: PlotTabPayload) -> Path:
        export_dir = Path(self._export_folder) if self._export_folder else Path.home()
        title = self._sanitize_filename_component(payload.title)
        timestamp = self._format_timestamp(datetime.now())
        return export_dir / f"{title}_{timestamp}.html"

    def _build_save_filters(self) -> str:
        if self._kaleido_available:
            return "HTML (*.html);;PNG (*.png);;SVG (*.svg);;JSON (*.json)"
        return "HTML (*.html);;JSON (*.json)"

    @staticmethod
    def _infer_suffix_from_filter(selected_filter: str) -> str | None:
        filter_text = selected_filter.lower()
        if "*.png" in filter_text:
            return "png"
        if "*.svg" in filter_text:
            return "svg"
        if "*.json" in filter_text:
            return "json"
        if "*.html" in filter_text:
            return "html"
        return None

    @staticmethod
    def _sanitize_filename_component(value: str) -> str:
        sanitized = (
            value.strip()
            .replace("/", "-")
            .replace("\\", "-")
            .replace("?", "-")
            .replace("%", "-")
            .replace("*", "-")
            .replace(":", "-")
            .replace("|", "-")
            .replace('"', "-")
            .replace("<", "-")
            .replace(">", "-")
        )
        sanitized = " ".join(sanitized.split())[:80].rstrip(" -").strip()
        return sanitized or "plotly-visualization"

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        return value.strftime("%Y%m%dT%H%M%S")

    def _copy_source_to_clipboard(self, payload: PlotTabPayload) -> None:
        QApplication.clipboard().setText(payload.spec_source_text)

    def _copy_png_to_clipboard(self, tab_widget: QWidget) -> None:
        QApplication.clipboard().setPixmap(tab_widget.grab())

    def _format_tab_title(self, payload: PlotTabPayload) -> str:
        return self._texts.tab_title_template.format(
            index=payload.spec_index + 1,
            title=payload.title,
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
    toolbar: QToolBar
    rerender_action: QAction
    copy_source_action: QAction
    copy_png_action: QAction
    save_action: QAction
    web_view: QWebEngineView
    html_path: Path