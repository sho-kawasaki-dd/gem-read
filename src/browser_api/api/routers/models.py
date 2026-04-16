from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from browser_api.api.dependencies import BrowserAPIServices, get_services
from browser_api.api.error_handlers import to_http_exception
from browser_api.api.schemas.analyze import ModelListResponse

router = APIRouter(tags=["models"])
logger = logging.getLogger(__name__)


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    services: BrowserAPIServices = Depends(get_services),
) -> ModelListResponse:
    try:
        result = await services.analyze_service.list_models()
        return ModelListResponse.from_result(result)
    except Exception as exc:
        logger.exception("Unexpected browser API model listing error")
        raise to_http_exception(exc) from exc