from __future__ import annotations

import os

import dotenv

from pdf_epub_reader.utils.config import ENV_GEMINI_API_KEY, AppConfig, load_config


def load_runtime_config() -> AppConfig:
    """Load the same runtime config that the desktop app uses so model settings stay aligned."""

    dotenv.load_dotenv()
    return load_config()


def load_api_key() -> str | None:
    """Read the Gemini API key at process startup so the browser extension never stores it."""

    return os.environ.get(ENV_GEMINI_API_KEY)