"""Activity log write helper.

All services call write() after significant state transitions.
Reads happen through the activity route (GET /api/v1/tournaments/{id}/activity).
"""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog, ActorType


def write(
    db: Session,
    *,
    tournament_id: UUID,
    actor_type: ActorType,
    actor_display_name: str,
    action: str,
    description: str,
    actor_id: UUID | None = None,
    division_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> ActivityLog:
    """Insert an activity log entry.  The caller must commit the session."""
    entry = ActivityLog(
        tournament_id=tournament_id,
        division_id=division_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_display_name=actor_display_name,
        action=action,
        description=description,
        extra_metadata=metadata or {},
    )
    db.add(entry)
    return entry
