from functools import lru_cache
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from app.config import get_settings


@lru_cache
def _jwk_client() -> PyJWKClient:
    settings = get_settings()
    if not settings.supabase_jwks_url:
        raise RuntimeError("SUPABASE_JWKS_URL is not configured")
    return PyJWKClient(settings.supabase_jwks_url)


def verify_supabase_token(token: str) -> dict[Any, Any]:
    settings = get_settings()
    signing_key = _jwk_client().get_signing_key_from_jwt(token).key
    return jwt.decode(
        token,
        signing_key,
        algorithms=["RS256", "ES256"],
        audience=settings.supabase_audience,
    )


def is_admin_email(email: str) -> bool:
    return email.lower() in get_settings().admin_emails


def login_with_password(email: str, password: str) -> dict[Any, Any] | Any:
    settings = get_settings()
    if not settings.supabase_project_url:
        raise RuntimeError("SUPABASE_PROJECT_URL is not configured")
    url = f"{settings.supabase_project_url}/auth/v1/token?grant_type=password"
    response = httpx.post(
        url,
        json={"email": email, "password": password},
        headers={"apikey": settings.supabase_audience},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()
