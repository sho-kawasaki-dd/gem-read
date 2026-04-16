"""Local-only browser API process entrypoint."""

from __future__ import annotations

import os

import uvicorn

from browser_api.api.app import app

DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000


def main() -> None:
	"""Launch Uvicorn with localhost defaults so the extension only targets the local bridge."""
	host = os.environ.get("BROWSER_API_HOST", DEFAULT_API_HOST)
	port = int(os.environ.get("BROWSER_API_PORT", str(DEFAULT_API_PORT)))
	uvicorn.run("browser_api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
	main()