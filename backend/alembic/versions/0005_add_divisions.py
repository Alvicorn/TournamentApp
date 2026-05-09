"""add divisions table and wire division_id FK on participants

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    division_state = postgresql.ENUM(
        "setup",
        "round_robin",
        "play_ins",
        "semis",
        "finals",
        "completed",
        "paused",
        name="division_state",
        create_type=False,
    )
    division_state.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "divisions",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tournament_id", sa.UUID, sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column(
            "state",
            division_state,
            nullable=False,
            server_default="setup",
        ),
        sa.Column("paused_reason", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Now that divisions exists, add the FK constraint on participants
    op.create_foreign_key(
        "fk_participants_division_id",
        "participants",
        "divisions",
        ["division_id"],
        ["id"],
    )
    op.create_index(
        "ix_participants_division_withdrawn",
        "participants",
        ["division_id", "is_withdrawn"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_participants_division_withdrawn")
    op.drop_constraint("fk_participants_division_id", "participants", type_="foreignkey")
    op.drop_table("divisions")
    op.execute("DROP TYPE IF EXISTS division_state CASCADE")
