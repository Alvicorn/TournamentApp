"""Participant business logic."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.activity_log import ActorType
from app.models.participant import Participant
from app.models.tournament import LifecycleState
from app.schemas.participant import ParticipantCreate, ParticipantUpdate
from app.services import activity_log as al
from app.services.tournament import get_tournament_or_404


def create_participant(
    db: Session,
    tournament_id: UUID,
    body: ParticipantCreate,
    actor_id: str,
    actor_email: str,
) -> Participant:
    get_tournament_or_404(db, tournament_id)
    p = Participant(
        tournament_id=tournament_id,
        name=body.name,
        custom_fields=body.custom_fields,
    )
    db.add(p)
    db.flush()
    al.write(
        db,
        tournament_id=tournament_id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action="participant.added",
        description=f"Participant '{body.name}' added",
        metadata={"participant_id": str(p.id)},
    )
    db.commit()
    db.refresh(p)
    return p


def list_participants(db: Session, tournament_id: UUID) -> list[Participant]:
    get_tournament_or_404(db, tournament_id)
    stmt = select(Participant).where(
        Participant.tournament_id == tournament_id,
    )
    return list(db.execute(stmt).scalars())


def _get_participant_or_404(db: Session, participant_id: UUID) -> Participant:
    p = db.execute(
        select(Participant).where(
            Participant.id == participant_id,
        )
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participant not found")
    return p


def update_participant(
    db: Session,
    participant_id: UUID,
    body: ParticipantUpdate,
    actor_id: str,
    actor_email: str,
) -> Participant:
    p = _get_participant_or_404(db, participant_id)

    # Block updates once the tournament is completed
    t = get_tournament_or_404(db, p.tournament_id)
    if t.lifecycle_state == LifecycleState.completed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "TOURNAMENT_COMPLETED: participant updates are not allowed after tournament completion",
        )

    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(p, key, value)
    al.write(
        db,
        tournament_id=p.tournament_id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action="participant.updated",
        description=f"Participant '{p.name}' updated",
        metadata={"participant_id": str(participant_id), "fields": list(data.keys())},
    )
    db.commit()
    db.refresh(p)
    return p


def delete_participant(
    db: Session,
    participant_id: UUID,
    actor_id: str,
    actor_email: str,
) -> None:
    p = _get_participant_or_404(db, participant_id)

    # Check if participant has any matches (scheduled or otherwise)
    # Deferred import to avoid circular dependency (match → judge/participant → match)
    from app.models.match import Match

    has_matches = db.execute(
        select(Match).where(
            (Match.competitor_a_id == participant_id) | (Match.competitor_b_id == participant_id),
        )
    ).scalar_one_or_none()

    if has_matches:
        p.is_withdrawn = True
        action = "participant.withdrawn"
        desc = f"Participant '{p.name}' marked as withdrawn"
    else:
        db.execute(
            text("DELETE FROM participants WHERE id = :id"),
            {"id": participant_id},
        )
        action = "participant.removed"
        desc = f"Participant '{p.name}' removed"

    al.write(
        db,
        tournament_id=p.tournament_id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action=action,
        description=desc,
        metadata={"participant_id": str(participant_id)},
    )
    db.commit()
