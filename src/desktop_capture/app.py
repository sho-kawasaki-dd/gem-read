"""Desktop capture application bootstrap and temporary Phase 1A shell."""

from __future__ import annotations

import ctypes
import logging

import dotenv
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from pdf_epub_reader.infrastructure.event_loop import run_app

from desktop_capture.config import DesktopCaptureConfig, load_config

logger = logging.getLogger(__name__)

_bootstrap_window: QWidget | None = None


def main() -> None:
    """Start the desktop capture application bootstrap."""
    dotenv.load_dotenv()
    _enable_dpi_awareness()
    run_app(_app_main)


def _enable_dpi_awareness() -> None:
    """Opt into per-monitor DPI awareness before QApplication is created."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except AttributeError:
        logger.debug("SetProcessDpiAwareness is not available on this platform")
    except OSError as exc:
        logger.debug("Failed to enable per-monitor DPI awareness: %s", exc)


async def _app_main() -> None:
    """Load initial config and show the temporary bootstrap window."""
    global _bootstrap_window  # noqa: PLW0603

    config = load_config()
    _bootstrap_window = _create_bootstrap_window(config)
    _bootstrap_window.show()


def _create_bootstrap_window(config: DesktopCaptureConfig) -> QWidget:
    window = QWidget()
    window.setWindowTitle("Desktop Capture")
    window.resize(480, 220)

    title_label = QLabel("Desktop Capture bootstrap is ready.")
    title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

    summary_label = QLabel(
        "Phase 1A initialized the standalone app shell.\n\n"
        f"Capture backend: {config.capture_backend}\n"
        f"OCR backend: {config.ocr_backend}\n"
        f"Default delayed capture: {config.delayed_capture_seconds}s\n"
        f"Hotkey: {config.hotkey or 'not configured'}"
    )
    summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

    layout = QVBoxLayout()
    layout.addWidget(title_label)
    layout.addWidget(summary_label)
    layout.addStretch()
    window.setLayout(layout)
    return window