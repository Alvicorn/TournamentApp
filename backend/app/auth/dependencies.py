# from dataclasses import dataclass
# from typing import Annotated, Literal
# from uuid import UUID

# from fastapi import Depends, Header, HTTPException, status

# from app.auth.judge import decode_judge_token
# from app.auth.supabase import is_admin_email, verify_supabase_token


# @dataclass
# class AdminPrincipal:
#     role: Literal["admin"]
#     user_id: str
#     email: str


# @dataclass
# class JudgePrincipal:
#     role: Literal["judge"]
#     judge_id: UUID
#     tournament_id: UUID
#     jti: UUID


# def _bearer(authorization: str | None) -> str:
#     if not authorization or not authorization.lower().startswith("bearer "):
#         raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
#     return authorization.split(" ", 1)[1]


# def require_admin(authorization: Annotated[str | None, Header()] = None) -> AdminPrincipal:
#     token = _bearer(authorization)
#     try:
#         claims = verify_supabase_token(token)
#     except Exception as exc:
#         raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
#     email = claims.get("email", "")
#     if not is_admin_email(email):
#         raise HTTPException(status.HTTP_403_FORBIDDEN, "Not an allow-listed admin")
#     return AdminPrincipal(role="admin", user_id=str(claims.get("sub", "")), email=email)


# def require_judge(authorization: Annotated[str | None, Header()] = None) -> JudgePrincipal:
#     token = _bearer(authorization)
#     try:
#         claims = decode_judge_token(token)
#     except Exception as exc:
#         raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
#     if claims.get("role") != "judge":
#         raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
#     return JudgePrincipal(
#         role="judge",
#         judge_id=UUID(claims["sub"]),
#         tournament_id=UUID(claims["tournament_id"]),
#         jti=UUID(claims["jti"]),
#     )


# AdminUser = Annotated[AdminPrincipal, Depends(require_admin)]
# JudgeUser = Annotated[JudgePrincipal, Depends(require_judge)]
