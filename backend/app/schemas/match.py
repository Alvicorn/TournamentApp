"""Match Pydantic schemas."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.match import MatchPhase, MatchState


class MatchOut(BaseModel):
    id: UUID
    division_id: UUID
    competitor_a_id: UUID
    competitor_b_id: UUID
    phase: MatchPhase
    order_index: int
    state: MatchState
    assigned_judge_id: UUID | None
    winner_id: UUID | None
    forfeit_by_id: UUID | None
    current_round: int
    is_sudden_death: bool

    model_config = {"from_attributes": True}


class ReorderBody(BaseModel):
    ordered_match_ids: list[UUID]


class RoundScoreIn(BaseModel):
    round_number: int
    competitor_a_score: int
    competitor_b_score: int


class EditResultBody(BaseModel):
    round_scores: list[RoundScoreIn] = Field(min_length=1)
