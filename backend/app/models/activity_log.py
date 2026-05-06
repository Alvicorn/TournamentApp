"""ActivityLog ORM model."""

import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class ActorType(enum.StrEnum):
    admin = "admin"
    judge = "judge"
    system = "system"


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[UUID] = uuid_pk()
    tournament_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False
    )
    division_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("divisions.id"), nullable=True
    )
    actor_type: Mapped[ActorType] = mapped_column(
        SAEnum(ActorType, name="actor_type", create_type=False), nullable=False
    )
    actor_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    actor_display_name: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
