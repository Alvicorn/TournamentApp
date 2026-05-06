"""add judges table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "judges",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tournament_id", sa.UUID, sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("code", sa.Text, nullable=False),
        sa.Column("current_session_jti", sa.UUID, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_judges_tournament_code", "judges", ["tournament_id", "code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_judges_tournament_code")
    op.drop_table("judges")
