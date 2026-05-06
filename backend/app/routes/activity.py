"""Activity log route — GET /api/v1/tournaments/{id}/activity"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.db import get_db
from app.models.activity_log import ActivityLog
from app.schemas.activity_log import ActivityLogOut

router = APIRouter(tags=["activity"])


@router.get("/tournaments/{tournament_id}/activity", response_model=list[ActivityLogOut])
def list_activity(
    tournament_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
    since: datetime | None = Query(default=None),  # noqa: B008
    division_id: UUID | None = Query(default=None),  # noqa: B008
    limit: int = Query(default=50, le=200),  # noqa: B008
) -> list[ActivityLogOut]:
    stmt = (
        select(ActivityLog)
        .where(ActivityLog.tournament_id == tournament_id)
        .order_by(ActivityLog.created_at.desc())
    )
    if since:
        stmt = stmt.where(ActivityLog.created_at > since)
    if division_id:
        stmt = stmt.where(ActivityLog.division_id == division_id)
    stmt = stmt.limit(limit)
    return list(db.execute(stmt).scalars())  # type: ignore[arg-type]
