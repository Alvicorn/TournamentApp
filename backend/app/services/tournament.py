"""Tournament business logic."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.activity_log import ActorType
from app.models.tournament import LifecycleState, Tournament
from app.schemas.tournament import TournamentCreate, TournamentUpdate
from app.services import activity_log as al

# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def get_active_tournament(db: Session) -> Tournament:
    """Return the single non-demo, non-completed tournament, or raise 404."""
    stmt = select(Tournament).where(
        Tournament.is_demo.is_(False),
        Tournament.lifecycle_state != LifecycleState.completed,
    )
    t = db.execute(stmt).scalar_one_or_none()
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active tournament")
    return t


def get_tournament_or_404(db: Session, tournament_id: UUID) -> Tournament:
    stmt = select(Tournament).where(
        Tournament.id == tournament_id,
    )
    t = db.execute(stmt).scalar_one_or_none()
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tournament not found")
    return t


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def create_tournament(
    db: Session,
    body: TournamentCreate,
    actor_id: str,
    actor_email: str,
) -> Tournament:
    # Enforce one-active-non-demo constraint
    if not body.is_demo:
        conflict = db.execute(
            select(Tournament).where(
                Tournament.is_demo.is_(False),
                Tournament.lifecycle_state != LifecycleState.completed,
            )
        ).scalar_one_or_none()
        if conflict:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "An active non-demo tournament already exists",
            )

    fields = body.model_dump()
    fields["custom_participant_fields"] = [f.model_dump() for f in body.custom_participant_fields]
    t = Tournament(**fields)
    db.add(t)
    db.flush()  # get id before activity log

    al.write(
        db,
        tournament_id=t.id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action="tournament.created",
        description=f"Tournament '{t.name}' created",
    )
    db.commit()
    db.refresh(t)
    return t


def update_tournament(
    db: Session,
    tournament_id: UUID,
    body: TournamentUpdate,
    actor_id: str,
    actor_email: str,
) -> Tournament:
    t = get_tournament_or_404(db, tournament_id)

    data = body.model_dump(exclude_unset=True)

    # Freeze check — reject custom_participant_fields changes when not in setup
    if "custom_participant_fields" in data and t.lifecycle_state != LifecycleState.setup:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "CUSTOM_FIELDS_FROZEN: custom_participant_fields cannot be changed after activation",
        )

    for key, value in data.items():
        if key == "custom_participant_fields" and value is not None:
            value = [f if isinstance(f, dict) else f.model_dump() for f in value]
        setattr(t, key, value)

    al.write(
        db,
        tournament_id=t.id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action="tournament.updated",
        description=f"Tournament '{t.name}' updated",
        metadata={"fields": list(data.keys())},
    )
    db.commit()
    db.refresh(t)
    return t


def transition_lifecycle(
    db: Session,
    tournament_id: UUID,
    new_state: LifecycleState,
    actor_id: str,
    actor_email: str,
) -> Tournament:
    t = get_tournament_or_404(db, tournament_id)

    # Validate transition
    allowed: dict[LifecycleState, list[LifecycleState]] = {
        LifecycleState.setup: [LifecycleState.active],
        LifecycleState.active: [LifecycleState.completed],
        LifecycleState.completed: [],
    }
    if new_state not in allowed[t.lifecycle_state]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot transition from {t.lifecycle_state} to {new_state}",
        )

    t.lifecycle_state = new_state
    action = (
        "tournament.activated" if new_state == LifecycleState.active else "tournament.completed"
    )
    al.write(
        db,
        tournament_id=t.id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action=action,
        description=f"Tournament '{t.name}' transitioned to {new_state}",
    )
    db.commit()
    db.refresh(t)
    return t


def delete_tournament(
    db: Session,
    tournament_id: UUID,
    actor_id: str,
    actor_email: str,
) -> None:
    get_tournament_or_404(db, tournament_id)
    db.execute(
        text(
            "DELETE FROM score_events WHERE match_id IN "
            "(SELECT id FROM matches WHERE division_id IN "
            "  (SELECT id FROM divisions WHERE tournament_id = :tid))"
        ),
        {"tid": tournament_id},
    )
    db.execute(
        text(
            "DELETE FROM match_rounds WHERE match_id IN "
            "(SELECT id FROM matches WHERE division_id IN "
            "  (SELECT id FROM divisions WHERE tournament_id = :tid))"
        ),
        {"tid": tournament_id},
    )
    db.execute(
        text(
            "DELETE FROM matches WHERE division_id IN "
            "(SELECT id FROM divisions WHERE tournament_id = :tid)"
        ),
        {"tid": tournament_id},
    )
    db.execute(text("DELETE FROM activity_log WHERE tournament_id = :tid"), {"tid": tournament_id})
    db.execute(
        text("UPDATE participants SET division_id = NULL WHERE tournament_id = :tid"),
        {"tid": tournament_id},
    )
    db.execute(text("DELETE FROM participants WHERE tournament_id = :tid"), {"tid": tournament_id})
    db.execute(text("DELETE FROM judges WHERE tournament_id = :tid"), {"tid": tournament_id})
    db.execute(text("DELETE FROM divisions WHERE tournament_id = :tid"), {"tid": tournament_id})
    db.execute(text("DELETE FROM tournaments WHERE id = :id"), {"id": tournament_id})
    db.commit()


def reset_tournament(
    db: Session,
    tournament_id: UUID,
    actor_id: str,
    actor_email: str,
) -> Tournament:
    t = get_tournament_or_404(db, tournament_id)
    if not t.is_demo:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only demo tournaments can be reset",
        )

    db.execute(
        text(
            "DELETE FROM score_events WHERE match_id IN "
            "(SELECT id FROM matches WHERE division_id IN "
            "  (SELECT id FROM divisions WHERE tournament_id = :tid))"
        ),
        {"tid": tournament_id},
    )
    db.execute(
        text(
            "DELETE FROM match_rounds WHERE match_id IN "
            "(SELECT id FROM matches WHERE division_id IN "
            "  (SELECT id FROM divisions WHERE tournament_id = :tid))"
        ),
        {"tid": tournament_id},
    )
    db.execute(
        text(
            "DELETE FROM matches WHERE division_id IN "
            "(SELECT id FROM divisions WHERE tournament_id = :tid)"
        ),
        {"tid": tournament_id},
    )
    db.execute(text("DELETE FROM activity_log WHERE tournament_id = :tid"), {"tid": tournament_id})
    db.execute(
        text("UPDATE participants SET division_id = NULL WHERE tournament_id = :tid"),
        {"tid": tournament_id},
    )
    db.execute(text("DELETE FROM participants WHERE tournament_id = :tid"), {"tid": tournament_id})
    db.execute(text("DELETE FROM judges WHERE tournament_id = :tid"), {"tid": tournament_id})
    db.execute(text("DELETE FROM divisions WHERE tournament_id = :tid"), {"tid": tournament_id})

    t.lifecycle_state = LifecycleState.setup
    t.custom_participant_fields = []

    al.write(
        db,
        tournament_id=t.id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action="tournament.reset",
        description=f"Demo tournament '{t.name}' reset to setup state",
    )
    db.commit()
    db.refresh(t)
    return t
