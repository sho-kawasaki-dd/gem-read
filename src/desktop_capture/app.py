"""Desktop capture application bootstrap and temporary Phase 1A shell."""

from __future__ import annotations

import ctypes
import logging

import dotenv
from PySide6.QtWidgets import QWidget

from pdf_epub_reader.infrastructure.event_loop import run_app

from desktop_capture.config import DesktopCaptureConfig, load_config
from desktop_capture.contracts import CaptureFlowState
from desktop_capture.result_window import DesktopCaptureResultWindow

logger = logging.getLogger(__name__)

_bootstrap_window: DesktopCaptureResultWindow | None = None


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


def _create_bootstrap_window(config: DesktopCaptureConfig) -> DesktopCaptureResultWindow:
    window = DesktopCaptureResultWindow()
    window.show_status(CaptureFlowState.IDLE, "Desktop capture bootstrap is ready.")
    window.set_body_text(
        "Phase 1 bootstrap summary\n\n"
        f"Capture backend: {config.capture_backend}\n"
        f"OCR backend: {config.ocr_backend}\n"
        f"Default delayed capture: {config.delayed_capture_seconds}s\n"
        f"Hotkey: {config.hotkey or 'not configured'}"
    )
    return window