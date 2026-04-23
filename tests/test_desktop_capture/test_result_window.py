from __future__ import annotations

import os
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from pdf_epub_reader.dto.ai_dto import AnalysisResult

from desktop_capture.contracts import CaptureFlowState
from desktop_capture.result_window import DesktopCaptureResultWindow


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


def test_show_status_updates_state_and_message() -> None:
    _get_app()
    window = DesktopCaptureResultWindow()

    window.show_status(CaptureFlowState.ANALYZING, "Analyzing capture...")

    assert window.current_state_text() == "State: Analyzing"
    assert window.current_message_text() == "Analyzing capture..."
    assert window.current_body_text() == ""


def test_show_result_renders_translation_and_explanation_as_plain_text() -> None:
    _get_app()
    window = DesktopCaptureResultWindow()

    window.show_result(
        AnalysisResult(
            translated_text="Translated text",
            explanation="Short explanation",
        )
    )

    assert window.current_state_text() == "State: Result"
    assert window.current_body_text() == (
        "Translated text\n\n---\n\nExplanation\n\nShort explanation"
    )


def test_show_error_reuses_same_window_surface() -> None:
    _get_app()
    window = DesktopCaptureResultWindow()

    window.show_error("API key is missing.")

    assert window.current_state_text() == "State: Error"
    assert window.current_message_text() == "API key is missing."
    assert window.current_body_text() == "API key is missing."