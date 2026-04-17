from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from browser_api.api.dependencies import BrowserAPIServices, get_services
from browser_api.api.error_handlers import to_http_exception
from browser_api.api.schemas.tokens import TokenCountRequest, TokenCountResponse

router = APIRouter(prefix="/tokens", tags=["tokens"])
logger = logging.getLogger(__name__)


@router.post("/count", response_model=TokenCountResponse)
async def count_tokens(
    request: TokenCountRequest,
    services: BrowserAPIServices = Depends(get_services),
) -> TokenCountResponse:
    """Expose Gemini token counting for overlay preflight estimates."""

    try:
        result = await services.analyze_service.count_tokens(request.to_command())
        return TokenCountResponse.from_result(result)
    except Exception as exc:
        logger.exception("Unexpected browser API token count error")
        raise to_http_exception(exc) from exc