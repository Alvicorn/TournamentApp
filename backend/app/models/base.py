"""SQLAlchemy declarative base + shared mixins.

All timestamp columns use ``server_default=func.now()`` and ``onupdate=func.now()``
so the Postgres clock is the only authority. See ``docs/engineering/correctness.md``.

All deletes are soft deletes via ``deleted_at``.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Query, mapped_column


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """Adds ``deleted_at`` plus a ``soft_delete()`` helper.

    Always filter ``WHERE deleted_at IS NULL`` in list queries. The
    ``filter_active`` classmethod is a convenience for the common case.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    def soft_delete(self) -> None:
        # Service layer should overwrite via SQL ``UPDATE ... SET deleted_at = now()``
        # to use the DB clock; this Python fallback exists for tests / scripts.
        self.deleted_at = datetime.now()

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @classmethod
    def filter_active(cls, query: Query[Any]) -> Query[Any]:
        return query.filter(cls.deleted_at.is_(None))
