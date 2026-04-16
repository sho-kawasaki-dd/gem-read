from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return a minimal liveness signal so the extension can distinguish offline from degraded states."""

    return {"status": "ok"}