from __future__ import annotations

import os

import dotenv

from browser_api.application.config import (
    BrowserApiConfig,
    map_app_config_to_browser_api_config,
)
from pdf_epub_reader.utils.config import ENV_GEMINI_API_KEY, load_config


def load_runtime_config() -> BrowserApiConfig:
    """Load browser_api runtime settings through an explicit AppConfig mapping."""

    dotenv.load_dotenv()
    return map_app_config_to_browser_api_config(load_config())


def load_api_key() -> str | None:
    """Read the Gemini API key at process startup so the browser extension never stores it."""

    return os.environ.get(ENV_GEMINI_API_KEY)