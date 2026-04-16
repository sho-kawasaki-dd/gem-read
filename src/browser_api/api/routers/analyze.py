from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from browser_api.api.dependencies import BrowserAPIServices, get_services
from browser_api.api.error_handlers import to_http_exception
from browser_api.api.schemas.analyze import (
    AnalyzeTranslateRequest,
    AnalyzeTranslateResponse,
)
from browser_api.application.errors import InvalidImagePayloadError, MissingModelError
from pdf_epub_reader.utils.exceptions import AIAPIError

router = APIRouter(prefix="/analyze", tags=["analyze"])
logger = logging.getLogger(__name__)


@router.post("/translate", response_model=AnalyzeTranslateResponse)
async def analyze_translate(
    request: AnalyzeTranslateRequest,
    services: BrowserAPIServices = Depends(get_services),
) -> AnalyzeTranslateResponse:
    try:
        result = await services.analyze_service.analyze_translate(
            request.to_command()
        )
        return AnalyzeTranslateResponse.from_result(result)
    except (MissingModelError, InvalidImagePayloadError, AIAPIError) as exc:
        raise to_http_exception(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected browser API error")
        raise to_http_exception(exc) from exc