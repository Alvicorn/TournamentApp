"""Backup ORM model."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class BackupTrigger(enum.StrEnum):
    manual = "manual"
    pre_action = "pre_action"
    hourly = "hourly"


class BackupStatus(enum.StrEnum):
    pending = "pending"
    complete = "complete"
    failed = "failed"


class Backup(Base):
    __tablename__ = "backups"

    id: Mapped[UUID] = uuid_pk()
    tournament_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False
    )
    triggered_by: Mapped[BackupTrigger] = mapped_column(
        SAEnum(BackupTrigger, name="backup_trigger", create_type=False), nullable=False
    )
    pre_action_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[BackupStatus] = mapped_column(
        SAEnum(BackupStatus, name="backup_status", create_type=False),
        nullable=False,
        server_default=BackupStatus.pending.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
