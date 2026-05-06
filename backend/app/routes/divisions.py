"""Division routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.db import get_db
from app.schemas.division import (
    AssignParticipantBody,
    DivisionCreate,
    DivisionOut,
    DivisionUpdate,
    MoveParticipantBody,
)
from app.services import division as svc

router = APIRouter(tags=["divisions"])


@router.post(
    "/tournaments/{tournament_id}/divisions",
    status_code=status.HTTP_201_CREATED,
    response_model=DivisionOut,
)
def create_division(
    tournament_id: UUID,
    body: DivisionCreate,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> DivisionOut:
    return svc.create_division(
        db, tournament_id, body, actor_id=admin.user_id, actor_email=admin.email
    )


@router.get("/tournaments/{tournament_id}/divisions", response_model=list[DivisionOut])
def list_divisions(
    tournament_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[DivisionOut]:
    return svc.list_divisions(db, tournament_id)


@router.patch("/divisions/{division_id}", response_model=DivisionOut)
def update_division(
    division_id: UUID,
    body: DivisionUpdate,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> DivisionOut:
    return svc.update_division(
        db, division_id, body, actor_id=admin.user_id, actor_email=admin.email
    )


@router.post("/divisions/{division_id}/assign-participant", response_model=None)
def assign_participant(
    division_id: UUID,
    body: AssignParticipantBody,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    svc.assign_participant(db, division_id, body, actor_id=admin.user_id, actor_email=admin.email)


@router.post("/divisions/{division_id}/move-participant", response_model=None)
def move_participant(
    division_id: UUID,
    body: MoveParticipantBody,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    svc.move_participant(db, division_id, body, actor_id=admin.user_id, actor_email=admin.email)


@router.post("/divisions/{division_id}/generate-round-robin", response_model=DivisionOut)
def generate_round_robin(
    division_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> DivisionOut:
    return svc.generate_division_round_robin(
        db, division_id, actor_id=admin.user_id, actor_email=admin.email
    )
