import httpx
from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.redis_client import ping_redis

router = APIRouter(tags=["health"])


def _ping_supabase() -> bool:
    settings = get_settings()
    if not settings.supabase_url:
        return False
    try:
        r = httpx.get(
            f"{settings.supabase_url}/rest/v1/",
            headers={"apikey": settings.supabase_key},
            timeout=5.0,
        )
        return r.status_code < 500
    except Exception:
        return False


@router.get("/health")
def health() -> dict[str, str]:
    if not _ping_supabase():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "supabase unreachable")
    return {"status": "ok"}


@router.get("/health/redis")
def health_redis() -> dict[str, str]:
    if not ping_redis():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "redis unreachable")
    return {"status": "ok"}
