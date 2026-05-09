"""add tournaments table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    lifecycle_state = postgresql.ENUM(
        "setup", "active", "completed", name="lifecycle_state", create_type=False
    )
    lifecycle_state.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tournaments",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("competition_date", sa.Date, nullable=False),
        sa.Column("time_zone", sa.Text, nullable=False),
        sa.Column("rounds_per_match", sa.Integer, nullable=False),
        sa.Column("round_length_seconds", sa.Integer, nullable=False),
        sa.Column("slideshow_slide_seconds", sa.Integer, nullable=False),
        sa.Column(
            "lifecycle_state",
            lifecycle_state,
            nullable=False,
            server_default="setup",
        ),
        sa.Column(
            "custom_participant_fields",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("judge_auto_release_seconds", sa.Integer, nullable=False, server_default="600"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("tournaments")
    op.execute("DROP TYPE IF EXISTS lifecycle_state CASCADE")
