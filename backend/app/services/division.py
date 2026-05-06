"""Division business logic — CRUD, participant assignment, round-robin generation."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity_log import ActorType
from app.models.division import Division, DivisionState
from app.models.match import Match, MatchPhase, MatchState
from app.models.participant import Participant
from app.schemas.division import (
    AssignParticipantBody,
    DivisionCreate,
    DivisionUpdate,
    MoveParticipantBody,
)
from app.services import activity_log as al
from app.services.round_robin import generate_round_robin
from app.services.tournament import get_tournament_or_404

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_division_or_404(db: Session, division_id: UUID) -> Division:
    d = db.execute(
        select(Division).where(Division.id == division_id, Division.deleted_at.is_(None))
    ).scalar_one_or_none()
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Division not found")
    return d


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def create_division(
    db: Session, tournament_id: UUID, body: DivisionCreate, actor_id: str, actor_email: str
) -> Division:
    get_tournament_or_404(db, tournament_id)
    d = Division(tournament_id=tournament_id, name=body.name)
    db.add(d)
    db.flush()
    al.write(
        db,
        tournament_id=tournament_id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action="division.created",
        description=f"Division '{body.name}' created",
        division_id=d.id,
    )
    db.commit()
    db.refresh(d)
    return d


def list_divisions(db: Session, tournament_id: UUID) -> list[Division]:
    get_tournament_or_404(db, tournament_id)
    return list(
        db.execute(
            select(Division).where(
                Division.tournament_id == tournament_id, Division.deleted_at.is_(None)
            )
        ).scalars()
    )


def update_division(
    db: Session, division_id: UUID, body: DivisionUpdate, actor_id: str, actor_email: str
) -> Division:
    d = _get_division_or_404(db, division_id)
    data = body.model_dump(exclude_unset=True)

    old_state = d.state
    for key, value in data.items():
        setattr(d, key, value)

    new_state = d.state
    if old_state != new_state:
        action = "division.paused" if new_state == DivisionState.paused else "division.resumed"
        al.write(
            db,
            tournament_id=d.tournament_id,
            actor_type=ActorType.admin,
            actor_id=UUID(actor_id),
            actor_display_name=actor_email,
            action=action,
            description=f"Division '{d.name}' {action.split('.')[1]}",
            division_id=d.id,
        )
    db.commit()
    db.refresh(d)
    return d


# ---------------------------------------------------------------------------
# Participant assignment
# ---------------------------------------------------------------------------


def assign_participant(
    db: Session,
    division_id: UUID,
    body: AssignParticipantBody,
    actor_id: str,
    actor_email: str,
) -> None:
    d = _get_division_or_404(db, division_id)

    # Participant must exist and not already be in a division
    p = db.execute(
        select(Participant).where(
            Participant.id == body.participant_id,
            Participant.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participant not found")
    if p.division_id is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "ALREADY_IN_DIVISION: participant is already assigned to a division",
        )

    # State-based branching
    post_rr_states = {
        DivisionState.play_ins,
        DivisionState.semis,
        DivisionState.finals,
        DivisionState.completed,
    }
    if d.state in post_rr_states:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "DIVISION_ADVANCED: division has advanced past round-robin; late additions not allowed",
        )

    p.division_id = division_id

    if d.state == DivisionState.round_robin:
        # Late addition: generate matches against every existing non-withdrawn participant
        existing = list(
            db.execute(
                select(Participant).where(
                    Participant.division_id == division_id,
                    Participant.id != body.participant_id,
                    Participant.is_withdrawn.is_(False),
                    Participant.deleted_at.is_(None),
                )
            ).scalars()
        )

        if existing:
            max_order = (
                db.execute(
                    select(func.max(Match.order_index)).where(
                        Match.division_id == division_id, Match.deleted_at.is_(None)
                    )
                ).scalar()
                or -1
            )

            new_matches = []
            for i, opponent in enumerate(existing):
                new_matches.append(
                    Match(
                        division_id=division_id,
                        competitor_a_id=body.participant_id,
                        competitor_b_id=opponent.id,
                        phase=MatchPhase.round_robin,
                        order_index=max_order + 1 + i,
                        state=MatchState.scheduled,
                    )
                )
            db.add_all(new_matches)
            al.write(
                db,
                tournament_id=d.tournament_id,
                division_id=division_id,
                actor_type=ActorType.admin,
                actor_id=UUID(actor_id),
                actor_display_name=actor_email,
                action="participant.added_late",
                description=f"Participant '{p.name}' added late — {len(new_matches)} new matches appended",
                metadata={"participant_id": str(p.id), "new_match_count": len(new_matches)},
            )
    else:
        al.write(
            db,
            tournament_id=d.tournament_id,
            division_id=division_id,
            actor_type=ActorType.admin,
            actor_id=UUID(actor_id),
            actor_display_name=actor_email,
            action="participant.added",
            description=f"Participant '{p.name}' assigned to division '{d.name}'",
            metadata={"participant_id": str(p.id)},
        )

    db.commit()


def move_participant(
    db: Session,
    division_id: UUID,
    body: MoveParticipantBody,
    actor_id: str,
    actor_email: str,
) -> None:
    source = _get_division_or_404(db, division_id)
    target = _get_division_or_404(db, body.target_division_id)

    if source.state != DivisionState.setup or target.state != DivisionState.setup:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Participant moves are only allowed when both divisions are in setup state",
        )

    p = db.execute(
        select(Participant).where(
            Participant.id == body.participant_id,
            Participant.division_id == division_id,
            Participant.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participant not found in this division")

    p.division_id = body.target_division_id
    db.commit()


# ---------------------------------------------------------------------------
# Round-robin generation
# ---------------------------------------------------------------------------


def generate_division_round_robin(
    db: Session,
    division_id: UUID,
    actor_id: str,
    actor_email: str,
) -> Division:
    d = _get_division_or_404(db, division_id)

    if d.state != DivisionState.setup:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Round-robin already generated (division state: {d.state})",
        )

    participants = list(
        db.execute(
            select(Participant).where(
                Participant.division_id == division_id,
                Participant.is_withdrawn.is_(False),
                Participant.deleted_at.is_(None),
            )
        ).scalars()
    )

    if len(participants) < 2:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Need at least 2 participants to generate round-robin"
        )

    pairs = generate_round_robin([p.id for p in participants])
    matches = [
        Match(
            division_id=division_id,
            competitor_a_id=a,
            competitor_b_id=b,
            phase=MatchPhase.round_robin,
            order_index=i,
            state=MatchState.scheduled,
        )
        for i, (a, b) in enumerate(pairs)
    ]
    db.add_all(matches)
    d.state = DivisionState.round_robin

    al.write(
        db,
        tournament_id=d.tournament_id,
        division_id=division_id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action="division.round_robin_generated",
        description=f"Round-robin generated for division '{d.name}' — {len(matches)} matches",
        metadata={"match_count": len(matches), "participant_count": len(participants)},
    )
    db.commit()
    db.refresh(d)
    return d
