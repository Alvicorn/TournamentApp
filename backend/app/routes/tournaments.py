"""Tournament routes — /api/v1/tournaments/*"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.db import get_db
from app.models.tournament import LifecycleState
from app.schemas.tournament import (
    LifecycleTransition,
    TournamentCreate,
    TournamentOut,
    TournamentUpdate,
)
from app.services import tournament as svc

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TournamentOut)
def create_tournament(
    body: TournamentCreate,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> TournamentOut:
    return svc.create_tournament(db, body, actor_id=admin.user_id, actor_email=admin.email)


@router.get("/active", response_model=TournamentOut)
def get_active(db: Session = Depends(get_db)) -> TournamentOut:  # noqa: B008
    return svc.get_active_tournament(db)


@router.patch("/{tournament_id}", response_model=TournamentOut)
def update_tournament(
    tournament_id: UUID,
    body: TournamentUpdate,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> TournamentOut:
    return svc.update_tournament(
        db, tournament_id, body, actor_id=admin.user_id, actor_email=admin.email
    )


@router.post("/{tournament_id}/lifecycle", response_model=TournamentOut)
def transition_lifecycle(
    tournament_id: UUID,
    body: LifecycleTransition,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> TournamentOut:
    return svc.transition_lifecycle(
        db, tournament_id, body.state, actor_id=admin.user_id, actor_email=admin.email
    )


@router.post("/{tournament_id}/reset", response_model=TournamentOut)
def reset_tournament(
    tournament_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> TournamentOut:
    return svc.reset_tournament(db, tournament_id, actor_id=admin.user_id, actor_email=admin.email)


@router.delete("/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tournament(
    tournament_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    t = svc.get_tournament_or_404(db, tournament_id)
    if t.lifecycle_state not in (LifecycleState.completed,) and not t.is_demo:
        raise HTTPException(409, "Only demo or completed tournaments can be deleted")
    svc.delete_tournament(db, tournament_id, actor_id=admin.user_id, actor_email=admin.email)


@router.get("/{tournament_id}/unclaimed-summary")
def unclaimed_summary(tournament_id: UUID, admin: AdminUser) -> dict:
    """Phase 2 stub — always returns zero. Phase 3 wires the real query."""
    return {"unclaimed_count": 0, "division_count": 0}
