"""Participant Pydantic schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ParticipantCreate(BaseModel):
    name: str
    custom_fields: dict[str, Any] = {}


class ParticipantUpdate(BaseModel):
    name: str | None = None
    custom_fields: dict[str, Any] | None = None


class ParticipantOut(BaseModel):
    id: UUID
    tournament_id: UUID
    division_id: UUID | None
    name: str
    custom_fields: dict[str, Any]
    is_withdrawn: bool
    created_at: datetime

    model_config = {"from_attributes": True}
