"""Participant routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.db import get_db
from app.models.participant import Participant
from app.schemas.participant import ParticipantCreate, ParticipantOut, ParticipantUpdate
from app.services import participant as svc

router = APIRouter(tags=["participants"])


@router.post(
    "/tournaments/{tournament_id}/participants",
    status_code=status.HTTP_201_CREATED,
    response_model=ParticipantOut,
)
def create_participant(
    tournament_id: UUID,
    body: ParticipantCreate,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> Participant:
    return svc.create_participant(
        db, tournament_id, body, actor_id=admin.user_id, actor_email=admin.email
    )


@router.get("/tournaments/{tournament_id}/participants", response_model=list[ParticipantOut])
def list_participants(
    tournament_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[Participant]:
    return svc.list_participants(db, tournament_id)


@router.patch("/participants/{participant_id}", response_model=ParticipantOut)
def update_participant(
    participant_id: UUID,
    body: ParticipantUpdate,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> Participant:
    return svc.update_participant(
        db, participant_id, body, actor_id=admin.user_id, actor_email=admin.email
    )


@router.delete("/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_participant(
    participant_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    svc.delete_participant(db, participant_id, actor_id=admin.user_id, actor_email=admin.email)
