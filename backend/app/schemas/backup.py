"""Backup Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.backup import BackupStatus, BackupTrigger


class BackupOut(BaseModel):
    id: UUID
    tournament_id: UUID
    triggered_by: BackupTrigger
    pre_action_description: str | None
    s3_key: str | None
    size_bytes: int | None
    status: BackupStatus
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
