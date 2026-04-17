from __future__ import annotations

from fastapi import HTTPException

from browser_api.application.errors import (
    InvalidImagePayloadError,
    MissingModelError,
    UnsupportedCacheModelError,
)
from pdf_epub_reader.utils.exceptions import AICacheError, AIAPIError, AIKeyMissingError


def to_http_exception(error: Exception) -> HTTPException:
    """Translate application and upstream errors into stable HTTP responses for the extension."""

    if isinstance(
        error,
        MissingModelError | InvalidImagePayloadError | UnsupportedCacheModelError,
    ):
        return HTTPException(status_code=400, detail=str(error))

    if isinstance(error, AIKeyMissingError):
        detail = str(error) or "GEMINI_API_KEY is not configured."
        return HTTPException(status_code=503, detail=detail)

    if isinstance(error, AICacheError):
        detail = str(error) or "Context cache operation failed."
        return HTTPException(status_code=502, detail=detail)

    if isinstance(error, AIAPIError):
        status_code = error.status_code if error.status_code else 502
        return HTTPException(status_code=status_code, detail=error.message)

    return HTTPException(status_code=500, detail="Unexpected browser API error.")