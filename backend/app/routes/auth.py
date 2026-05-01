# """Auth routes — Phase 1 skeleton.

# Admin login proxies to Supabase. Judge login is a stub here; the full implementation
# (judge lookup by code + jti tracking) lands in Phase 2 alongside the judges table.
# """

# from typing import Any
# from uuid import UUID

# from fastapi import APIRouter, HTTPException, status
# from pydantic import BaseModel, EmailStr

# from app.auth.judge import issue_judge_token
# from app.auth.supabase import is_admin_email, login_with_password
# from app.codes import is_valid_judge_code

# router = APIRouter(prefix="/auth", tags=["auth"])


# class AdminLoginBody(BaseModel):
#     email: EmailStr
#     password: str


# class JudgeLoginBody(BaseModel):
#     tournament_id: UUID
#     code: str


# @router.post("/admin/login")
# def admin_login(body: AdminLoginBody) -> dict[Any, Any] | Any:
#     if not is_admin_email(body.email):
#         raise HTTPException(status.HTTP_403_FORBIDDEN, "Not an allow-listed admin")
#     try:
#         return login_with_password(body.email, body.password)
#     except Exception as exc:
#         raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials") from exc


# @router.post("/judge/login")
# def judge_login(body: JudgeLoginBody) -> dict[Any, Any] | Any:
#     # Phase 1 skeleton: validate the code shape but don't look up a judge yet.
#     # Phase 3 plugs the DB lookup and current_session_jti tracking.
#     if not is_valid_judge_code(body.code):
#         raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Code not recognized")
#     raise HTTPException(
#         status.HTTP_501_NOT_IMPLEMENTED,
#         "Judge login is implemented in Phase 3 alongside the judges table",
#     )


# # The signing helper is exposed here so future routes (e.g. preview-as) can mint tokens.
# __all__ = ["router", "issue_judge_token"]
