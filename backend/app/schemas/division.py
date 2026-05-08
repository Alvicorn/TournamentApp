"""Division Pydantic schemas."""

from uuid import UUID

from pydantic import BaseModel

from app.models.division import DivisionState


class DivisionCreate(BaseModel):
    name: str


class DivisionUpdate(BaseModel):
    name: str | None = None
    state: DivisionState | None = None  # for pause/resume
    paused_reason: str | None = None


class AssignParticipantBody(BaseModel):
    participant_id: UUID


class MoveParticipantBody(BaseModel):
    participant_id: UUID
    target_division_id: UUID


class DivisionOut(BaseModel):
    id: UUID
    tournament_id: UUID
    name: str
    state: DivisionState
    paused_reason: str | None

    model_config = {"from_attributes": True}
