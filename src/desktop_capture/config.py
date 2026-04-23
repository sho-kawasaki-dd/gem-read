"""Desktop capture app configuration and persistence helpers."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import platformdirs

logger = logging.getLogger(__name__)

_APP_NAME = "gem-read-capture"
_APP_AUTHOR = "gem-read"

DEFAULT_CAPTURE_BACKEND: Literal["mss", "wgc"] = "mss"
DEFAULT_OCR_BACKEND: Literal["windows", "rapidocr"] = "windows"
DEFAULT_DELAYED_CAPTURE_SECONDS = 3
DEFAULT_GEMINI_MODEL = ""
DEFAULT_OUTPUT_LANGUAGE = "日本語"
DEFAULT_HOTKEY = "Ctrl+Shift+G"
DEFAULT_SYSTEM_PROMPT = (
    "You are a translator and annotator. Translate the given text into {output_language}.\n"
    "Assume the source is primarily horizontal Japanese text for now.\n"
    "The input text may be extracted by OCR and may contain duplicated characters from ruby "
    "(furigana) annotations. Prefer the main body text over ruby and infer the correct text from context before translating.\n"
    "Output the response in Markdown format."
)


@dataclass
class DesktopCaptureConfig:
    """User-editable configuration for the desktop capture app."""

    ocr_backend: Literal["windows", "rapidocr"] = DEFAULT_OCR_BACKEND
    capture_backend: Literal["mss", "wgc"] = DEFAULT_CAPTURE_BACKEND
    delayed_capture_seconds: int = DEFAULT_DELAYED_CAPTURE_SECONDS
    gemini_model_name: str = DEFAULT_GEMINI_MODEL
    output_language: str = DEFAULT_OUTPUT_LANGUAGE
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    hotkey: str = DEFAULT_HOTKEY

    def __post_init__(self) -> None:
        self.gemini_model_name = self.gemini_model_name.strip()
        self.output_language = self.output_language.strip() or DEFAULT_OUTPUT_LANGUAGE
        self.system_prompt = self.system_prompt.strip() or DEFAULT_SYSTEM_PROMPT
        self.hotkey = self.hotkey.strip() or DEFAULT_HOTKEY
        if self.delayed_capture_seconds < 0:
            self.delayed_capture_seconds = DEFAULT_DELAYED_CAPTURE_SECONDS


def _get_config_path() -> Path:
    config_dir = Path(platformdirs.user_config_dir(_APP_NAME, _APP_AUTHOR))
    return config_dir / "config.json"


def load_config(path: Path | None = None) -> DesktopCaptureConfig:
    config_path = path or _get_config_path()
    if not config_path.exists():
        return DesktopCaptureConfig()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        known_fields = {f.name for f in DesktopCaptureConfig.__dataclass_fields__.values()}
        filtered = {key: value for key, value in data.items() if key in known_fields}
        return DesktopCaptureConfig(**filtered)
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        logger.warning("Failed to load desktop capture config: %s", exc)
        return DesktopCaptureConfig()


def save_config(config: DesktopCaptureConfig, path: Path | None = None) -> None:
    config_path = path or _get_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Failed to save desktop capture config: %s", exc)