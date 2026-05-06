"""Tournament Pydantic schemas."""

from datetime import date
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.tournament import LifecycleState


class CustomFieldSpec(BaseModel):
    key: str
    label: str
    type: Literal["text", "number", "select"]
    required: bool = False


class TournamentCreate(BaseModel):
    name: str
    competition_date: date
    time_zone: str
    rounds_per_match: int = Field(ge=1)
    round_length_seconds: int = Field(ge=30)
    slideshow_slide_seconds: int = Field(ge=5)
    is_demo: bool = False
    judge_auto_release_seconds: int = Field(default=600, ge=60)
    custom_participant_fields: list[CustomFieldSpec] = []


class TournamentUpdate(BaseModel):
    name: str | None = None
    competition_date: date | None = None
    time_zone: str | None = None
    rounds_per_match: int | None = Field(default=None, ge=1)
    round_length_seconds: int | None = Field(default=None, ge=30)
    slideshow_slide_seconds: int | None = Field(default=None, ge=5)
    judge_auto_release_seconds: int | None = Field(default=None, ge=60)
    custom_participant_fields: list[CustomFieldSpec] | None = None


class LifecycleTransition(BaseModel):
    state: LifecycleState


class TournamentOut(BaseModel):
    id: UUID
    name: str
    competition_date: date
    time_zone: str
    rounds_per_match: int
    round_length_seconds: int
    slideshow_slide_seconds: int
    lifecycle_state: LifecycleState
    custom_participant_fields: list[Any]
    is_demo: bool
    judge_auto_release_seconds: int

    model_config = {"from_attributes": True}
