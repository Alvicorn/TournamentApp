"""Judge Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class JudgeCreate(BaseModel):
    name: str


class JudgeOut(BaseModel):
    id: UUID
    tournament_id: UUID
    name: str
    code: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
