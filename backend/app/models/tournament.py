"""Tournament ORM model."""

import enum
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Date, Integer, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class LifecycleState(enum.StrEnum):
    setup = "setup"
    active = "active"
    completed = "completed"


class Tournament(Base, TimestampMixin):
    __tablename__ = "tournaments"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    competition_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_zone: Mapped[str] = mapped_column(Text, nullable=False)
    rounds_per_match: Mapped[int] = mapped_column(Integer, nullable=False)
    round_length_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    slideshow_slide_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        SAEnum(LifecycleState, name="lifecycle_state", create_type=False),
        nullable=False,
        server_default=LifecycleState.setup.value,
    )
    custom_participant_fields: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    judge_auto_release_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="600"
    )
