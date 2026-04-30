from redis import Redis

from app.config import get_settings

_settings = get_settings()

redis_client: Redis = Redis.from_url(_settings.redis_url, decode_responses=True)


def ping_redis() -> bool:
    try:
        return bool(redis_client.ping())
    except Exception:
        return False
