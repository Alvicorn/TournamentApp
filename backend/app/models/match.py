"""Match, MatchRound, ScoreEvent ORM models."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class MatchPhase(enum.StrEnum):
    round_robin = "round_robin"
    play_in = "play_in"
    semi = "semi"
    final = "final"
    bronze = "bronze"


class MatchState(enum.StrEnum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    paused = "paused"
    pending_review = "pending_review"
    submitted = "submitted"


class RoundState(enum.StrEnum):
    not_started = "not_started"
    running = "running"
    paused = "paused"
    completed = "completed"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[UUID] = uuid_pk()
    division_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("divisions.id"), nullable=False
    )
    competitor_a_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False
    )
    competitor_b_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False
    )
    phase: Mapped[MatchPhase] = mapped_column(
        SAEnum(MatchPhase, name="match_phase", create_type=False),
        nullable=False,
        server_default=MatchPhase.round_robin.value,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[MatchState] = mapped_column(
        SAEnum(MatchState, name="match_state", create_type=False),
        nullable=False,
        server_default=MatchState.scheduled.value,
    )
    assigned_judge_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("judges.id"), nullable=True
    )
    winner_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("participants.id"), nullable=True
    )
    forfeit_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("participants.id"), nullable=True
    )
    current_round: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    is_sudden_death: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatchRound(Base):
    __tablename__ = "match_rounds"

    id: Mapped[UUID] = uuid_pk()
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    competitor_a_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    competitor_b_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accumulated_paused_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    state: Mapped[RoundState] = mapped_column(
        SAEnum(RoundState, name="round_state", create_type=False),
        nullable=False,
        server_default=RoundState.not_started.value,
    )


class ScoreEvent(Base):
    __tablename__ = "score_events"

    id: Mapped[UUID] = uuid_pk()
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    competitor_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    client_event_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
