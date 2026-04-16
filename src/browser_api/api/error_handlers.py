from __future__ import annotations

from fastapi import HTTPException

from browser_api.application.errors import InvalidImagePayloadError, MissingModelError
from pdf_epub_reader.utils.exceptions import AIAPIError


def to_http_exception(error: Exception) -> HTTPException:
    """Translate application and upstream errors into stable HTTP responses for the extension."""

    if isinstance(error, MissingModelError | InvalidImagePayloadError):
        return HTTPException(status_code=400, detail=str(error))

    if isinstance(error, AIAPIError):
        status_code = error.status_code if error.status_code else 502
        return HTTPException(status_code=status_code, detail=error.message)

    return HTTPException(status_code=500, detail="Unexpected browser API error.")