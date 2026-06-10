import httpx
from fastapi import APIRouter, HTTPException, status

from app.config import get_settings

router = APIRouter(tags=["health"])


def _ping_database() -> bool:
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
def health_database() -> dict[str, str]:
    if not _ping_database():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "database unreachable")
    return {"status": "ok"}
