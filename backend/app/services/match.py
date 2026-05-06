"""Match business logic — listing, reorder, result editing."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity_log import ActorType
from app.models.division import Division, DivisionState
from app.models.match import Match, MatchRound, MatchState
from app.schemas.match import EditResultBody, ReorderBody
from app.services import activity_log as al


def _get_match_or_404(db: Session, match_id: UUID) -> Match:
    m = db.execute(
        select(Match).where(Match.id == match_id, Match.deleted_at.is_(None))
    ).scalar_one_or_none()
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    return m


def _get_division_or_404(db: Session, division_id: UUID) -> Division:
    d = db.execute(
        select(Division).where(Division.id == division_id, Division.deleted_at.is_(None))
    ).scalar_one_or_none()
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Division not found")
    return d


def list_matches(db: Session, division_id: UUID) -> list[Match]:
    _get_division_or_404(db, division_id)
    return list(
        db.execute(
            select(Match)
            .where(Match.division_id == division_id, Match.deleted_at.is_(None))
            .order_by(Match.order_index)
        ).scalars()
    )


def reorder_matches(
    db: Session,
    division_id: UUID,
    body: ReorderBody,
    actor_id: str,
    actor_email: str,
) -> list[Match]:
    d = _get_division_or_404(db, division_id)
    for new_index, match_id in enumerate(body.ordered_match_ids):
        m = db.execute(
            select(Match).where(
                Match.id == match_id,
                Match.division_id == division_id,
                Match.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if m is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Match {match_id} not found in division"
            )
        m.order_index = new_index

    al.write(
        db,
        tournament_id=d.tournament_id,
        division_id=division_id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action="match.reordered",
        description=f"Match order updated in division '{d.name}'",
    )
    db.commit()
    return list_matches(db, division_id)


def edit_result(
    db: Session,
    match_id: UUID,
    body: EditResultBody,
    actor_id: str,
    actor_email: str,
) -> Match:
    m = _get_match_or_404(db, match_id)

    # Guard: division must be round_robin
    d = _get_division_or_404(db, m.division_id)
    if d.state != DivisionState.round_robin:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"DIVISION_ADVANCED: result editing is only allowed during round-robin phase (current: {d.state})",
        )

    # Guard: match must be submitted
    if m.state != MatchState.submitted:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Match must be in 'submitted' state to edit result (current: {m.state})",
        )

    # Capture old values for activity log
    old_rounds = list(
        db.execute(select(MatchRound).where(MatchRound.match_id == match_id)).scalars()
    )
    old_scores = [
        {"round_number": r.round_number, "a": r.competitor_a_score, "b": r.competitor_b_score}
        for r in old_rounds
    ]
    old_winner = str(m.winner_id) if m.winner_id else None

    # Update round scores
    for rs in body.round_scores:
        rnd = db.execute(
            select(MatchRound).where(
                MatchRound.match_id == match_id,
                MatchRound.round_number == rs.round_number,
            )
        ).scalar_one_or_none()
        if rnd is None:
            rnd = MatchRound(
                match_id=match_id,
                round_number=rs.round_number,
                competitor_a_score=rs.competitor_a_score,
                competitor_b_score=rs.competitor_b_score,
            )
            db.add(rnd)
        else:
            rnd.competitor_a_score = rs.competitor_a_score
            rnd.competitor_b_score = rs.competitor_b_score

    db.flush()

    # Recompute winner from updated rounds
    all_rounds = list(
        db.execute(select(MatchRound).where(MatchRound.match_id == match_id)).scalars()
    )
    total_a = sum(r.competitor_a_score for r in all_rounds)
    total_b = sum(r.competitor_b_score for r in all_rounds)
    if total_a > total_b:
        m.winner_id = m.competitor_a_id
    elif total_b > total_a:
        m.winner_id = m.competitor_b_id

    al.write(
        db,
        tournament_id=d.tournament_id,
        division_id=m.division_id,
        actor_type=ActorType.admin,
        actor_id=UUID(actor_id),
        actor_display_name=actor_email,
        action="match.result_edited",
        description="Match result edited by admin",
        metadata={
            "match_id": str(match_id),
            "old_scores": old_scores,
            "old_winner": old_winner,
            "new_winner": str(m.winner_id) if m.winner_id else None,
        },
    )
    db.commit()
    db.refresh(m)
    return m
