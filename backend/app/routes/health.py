from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.db import engine
from app.redis_client import ping_redis

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "database unreachable") from exc
    return {"status": "ok"}


@router.get("/health/redis")
def health_redis() -> dict[str, str]:
    if not ping_redis():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "redis unreachable")
    return {"status": "ok"}
