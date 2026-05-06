"""Match routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.db import get_db
from app.schemas.match import EditResultBody, MatchOut, ReorderBody
from app.services import match as svc

router = APIRouter(tags=["matches"])


@router.get("/divisions/{division_id}/matches", response_model=list[MatchOut])
def list_matches(
    division_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[MatchOut]:
    return svc.list_matches(db, division_id)


@router.post("/divisions/{division_id}/reorder-matches", response_model=list[MatchOut])
def reorder_matches(
    division_id: UUID,
    body: ReorderBody,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[MatchOut]:
    return svc.reorder_matches(
        db, division_id, body, actor_id=admin.user_id, actor_email=admin.email
    )


@router.post(
    "/matches/{match_id}/edit-result",
    response_model=MatchOut,
    status_code=status.HTTP_200_OK,
)
def edit_result(
    match_id: UUID,
    body: EditResultBody,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> MatchOut:
    return svc.edit_result(db, match_id, body, actor_id=admin.user_id, actor_email=admin.email)
