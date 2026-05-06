"""ActivityLog Pydantic schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.activity_log import ActorType


class ActivityLogOut(BaseModel):
    id: UUID
    tournament_id: UUID
    division_id: UUID | None
    actor_type: ActorType
    actor_id: UUID | None
    actor_display_name: str
    action: str
    description: str
    metadata: dict[str, Any] = Field(alias="extra_metadata", default={})
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
