"""Participant ORM model."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[UUID] = uuid_pk()
    tournament_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False
    )
    division_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("divisions.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    custom_fields: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    is_withdrawn: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
