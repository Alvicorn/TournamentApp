"""add activity_log table

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    actor_type = postgresql.ENUM("admin", "judge", "system", name="actor_type", create_type=False)
    actor_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "activity_log",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tournament_id", sa.UUID, sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column("division_id", sa.UUID, sa.ForeignKey("divisions.id"), nullable=True),
        sa.Column(
            "actor_type",
            actor_type,
            nullable=False,
        ),
        sa.Column("actor_id", sa.UUID, nullable=True),
        sa.Column("actor_display_name", sa.Text, nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_activity_log_tournament_created",
        "activity_log",
        ["tournament_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_activity_log_tournament_created")
    op.drop_table("activity_log")
    op.execute("DROP TYPE IF EXISTS actor_type CASCADE")
