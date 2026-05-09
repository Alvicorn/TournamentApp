"""drop deleted_at columns and update partial indexes

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop partial indexes that referenced deleted_at before removing the column
    op.drop_index("ix_matches_division_order", table_name="matches")
    op.drop_index("ix_matches_judge_active", table_name="matches")
    op.drop_index("ix_participants_division_withdrawn", table_name="participants")

    # Drop deleted_at columns
    op.drop_column("tournaments", "deleted_at")
    op.drop_column("judges", "deleted_at")
    op.drop_column("participants", "deleted_at")
    op.drop_column("divisions", "deleted_at")
    op.drop_column("matches", "deleted_at")

    # Recreate indexes without deleted_at filter
    op.create_index(
        "ix_matches_division_order",
        "matches",
        ["division_id", "order_index"],
    )
    op.create_index(
        "ix_matches_judge_active",
        "matches",
        ["assigned_judge_id"],
        postgresql_where=sa.text("state = 'in_progress'"),
    )
    op.create_index(
        "ix_participants_division_withdrawn",
        "participants",
        ["division_id", "is_withdrawn"],
    )


def downgrade() -> None:
    op.drop_index("ix_participants_division_withdrawn", table_name="participants")
    op.drop_index("ix_matches_judge_active", table_name="matches")
    op.drop_index("ix_matches_division_order", table_name="matches")

    op.add_column("matches", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("divisions", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "participants", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("judges", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tournaments", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(
        "ix_matches_division_order",
        "matches",
        ["division_id", "order_index"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_matches_judge_active",
        "matches",
        ["assigned_judge_id"],
        postgresql_where=sa.text("state = 'in_progress' AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_participants_division_withdrawn",
        "participants",
        ["division_id", "is_withdrawn"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
