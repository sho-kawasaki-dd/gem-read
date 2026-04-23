"""Reusable result window for the desktop capture Phase 1 flow."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from pdf_epub_reader.dto.ai_dto import AnalysisResult

from desktop_capture.contracts import CaptureFlowState


class DesktopCaptureResultWindow(QWidget):
    """Modeless window that shows capture status, results, and errors."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Desktop Capture Result")
        self.resize(560, 420)

        layout = QVBoxLayout(self)

        self._heading_label = QLabel("Desktop Capture")
        self._heading_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(self._heading_label)

        self._state_label = QLabel("")
        self._state_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._state_label)

        self._message_label = QLabel("")
        self._message_label.setWordWrap(True)
        self._message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._message_label)

        self._content_edit = QPlainTextEdit()
        self._content_edit.setReadOnly(True)
        self._content_edit.setPlaceholderText("No capture result yet.")
        layout.addWidget(self._content_edit)

    def show_status(self, state: CaptureFlowState, message: str) -> None:
        """Update the window for an in-progress or terminal state."""
        self._state_label.setText(f"State: {self._state_text(state)}")
        self._message_label.setText(message)
        if state is not CaptureFlowState.SHOWING_RESULT:
            self._content_edit.clear()
            self._content_edit.setPlaceholderText(self._placeholder_text(state))
        self.show()
        self.raise_()
        self.activateWindow()

    def show_result(self, result: AnalysisResult) -> None:
        """Render the latest analysis result as plain text."""
        sections: list[str] = []
        if result.translated_text:
            sections.append(result.translated_text)
        if result.explanation:
            sections.append(f"Explanation\n\n{result.explanation}")
        if not sections:
            sections.append(result.raw_response or "No response content was returned.")

        self._state_label.setText(f"State: {self._state_text(CaptureFlowState.SHOWING_RESULT)}")
        self._content_edit.setPlainText("\n\n---\n\n".join(sections))
        self.show()
        self.raise_()
        self.activateWindow()

    def show_error(self, message: str) -> None:
        """Render an error state without opening a modal dialog."""
        self._state_label.setText(f"State: {self._state_text(CaptureFlowState.SHOWING_ERROR)}")
        self._message_label.setText(message)
        self._content_edit.setPlainText(message)
        self.show()
        self.raise_()
        self.activateWindow()

    def set_body_text(self, text: str) -> None:
        """Set freeform body text for bootstrap and diagnostic messages."""
        self._content_edit.setPlainText(text)

    def current_state_text(self) -> str:
        """Expose the rendered state text for focused tests."""
        return self._state_label.text()

    def current_message_text(self) -> str:
        """Expose the rendered status/error message for focused tests."""
        return self._message_label.text()

    def current_body_text(self) -> str:
        """Expose the rendered plain-text body for focused tests."""
        return self._content_edit.toPlainText()

    @staticmethod
    def _state_text(state: CaptureFlowState) -> str:
        labels = {
            CaptureFlowState.IDLE: "Idle",
            CaptureFlowState.SELECTING: "Selecting",
            CaptureFlowState.CAPTURING: "Capturing",
            CaptureFlowState.ANALYZING: "Analyzing",
            CaptureFlowState.SHOWING_RESULT: "Result",
            CaptureFlowState.SHOWING_ERROR: "Error",
        }
        return labels[state]

    @staticmethod
    def _placeholder_text(state: CaptureFlowState) -> str:
        placeholders = {
            CaptureFlowState.IDLE: "No capture result yet.",
            CaptureFlowState.SELECTING: "Drag a rectangle over the area you want to analyze.",
            CaptureFlowState.CAPTURING: "Capturing the selected area...",
            CaptureFlowState.ANALYZING: "Waiting for Gemini analysis...",
            CaptureFlowState.SHOWING_RESULT: "",
            CaptureFlowState.SHOWING_ERROR: "",
        }
        return placeholders[state]