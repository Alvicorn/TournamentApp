from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt

from app.config import get_settings


def issue_judge_token(
    judge_id: UUID, tournament_id: UUID, jti: UUID | None = None
) -> tuple[str, UUID]:
    settings = get_settings()
    token_jti = jti or uuid4()
    now = datetime.now(UTC)
    payload = {
        "sub": str(judge_id),
        "tournament_id": str(tournament_id),
        "jti": str(token_jti),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.judge_jwt_ttl_seconds)).timestamp()),
        "role": "judge",
    }
    token = jwt.encode(payload, settings.judge_jwt_secret, algorithm="HS256")
    return token, token_jti


def decode_judge_token(token: str) -> dict[Any, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.judge_jwt_secret, algorithms=["HS256"])
