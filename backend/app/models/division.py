"""Division ORM model."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class DivisionState(enum.StrEnum):
    setup = "setup"
    round_robin = "round_robin"
    play_ins = "play_ins"
    semis = "semis"
    finals = "finals"
    completed = "completed"
    paused = "paused"


class Division(Base):
    __tablename__ = "divisions"

    id: Mapped[UUID] = uuid_pk()
    tournament_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[DivisionState] = mapped_column(
        SAEnum(DivisionState, name="division_state", create_type=False),
        nullable=False,
        server_default=DivisionState.setup.value,
    )
    paused_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
