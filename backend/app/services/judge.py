"""Judge business logic — CRUD and code generation."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.codes import generate_judge_code
from app.models.activity_log import ActorType
from app.models.judge import Judge
from app.schemas.judge import JudgeCreate
from app.services import activity_log as al
from app.services.tournament import get_tournament_or_404


def _generate_unique_code(db: Session, tournament_id: UUID) -> str:
    """Generate a code that doesn't already exist for this tournament."""
    for _ in range(10):  # practically always succeeds on first try
        code = generate_judge_code()
        exists = db.execute(
            select(Judge).where(
                Judge.tournament_id == tournament_id,
                Judge.code == code,
                Judge.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if exists is None:
            return code
    raise RuntimeError("Could not generate a unique judge code after 10 attempts")


def create_judge(
    db: Session,
    tournament_id: UUID,
    body: JudgeCreate,
    actor_id: str,
    actor_email: str,
) -> Judge:
    get_tournament_or_404(db, tournament_id)  # 404 if tournament missing
    code = _generate_unique_code(db, tournament_id)
    judge = Judge(tournament_id=tournament_id, name=body.name, code=code)
    db.add(judge)
    db.flush()
    al.write(
        db,
        tournament_id=tournament_id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action="judge.added",
        description=f"Judge '{body.name}' added",
        metadata={"judge_id": str(judge.id)},
    )
    db.commit()
    db.refresh(judge)
    return judge


def list_judges(db: Session, tournament_id: UUID) -> list[Judge]:
    get_tournament_or_404(db, tournament_id)
    stmt = select(Judge).where(
        Judge.tournament_id == tournament_id,
        Judge.deleted_at.is_(None),
    )
    return list(db.execute(stmt).scalars())


def delete_judge(
    db: Session,
    judge_id: UUID,
    actor_id: str,
    actor_email: str,
) -> None:
    judge = db.execute(
        select(Judge).where(Judge.id == judge_id, Judge.deleted_at.is_(None))
    ).scalar_one_or_none()
    if judge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Judge not found")

    # If judge has an active match, pause it and unassign
    # Deferred import to avoid circular dependency (match → judge/participant → match)
    from app.models.match import Match, MatchState

    active_match = db.execute(
        select(Match).where(
            Match.assigned_judge_id == judge_id,
            Match.state.in_([MatchState.in_progress, MatchState.paused, MatchState.pending_review]),
            Match.deleted_at.is_(None),
        )
    ).scalar_one_or_none()

    action = "judge.removed"
    if active_match:
        active_match.state = MatchState.paused
        active_match.assigned_judge_id = None
        action = "judge.removed_active"

    db.execute(
        text("UPDATE judges SET deleted_at = now(), current_session_jti = NULL WHERE id = :id"),
        {"id": judge_id},
    )
    al.write(
        db,
        tournament_id=judge.tournament_id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action=action,
        description=f"Judge '{judge.name}' removed",
        metadata={"judge_id": str(judge_id), "had_active_match": active_match is not None},
    )
    db.commit()
