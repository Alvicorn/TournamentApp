"""add matches, match_rounds, score_events tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE match_phase AS ENUM ('round_robin', 'play_in', 'semi', 'final', 'bronze')"
    )
    op.execute(
        "CREATE TYPE match_state AS ENUM "
        "('scheduled', 'in_progress', 'paused', 'pending_review', 'submitted')"
    )
    op.execute("CREATE TYPE round_state AS ENUM ('not_started', 'running', 'paused', 'completed')")
    op.create_table(
        "matches",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("division_id", sa.UUID, sa.ForeignKey("divisions.id"), nullable=False),
        sa.Column("competitor_a_id", sa.UUID, sa.ForeignKey("participants.id"), nullable=False),
        sa.Column("competitor_b_id", sa.UUID, sa.ForeignKey("participants.id"), nullable=False),
        sa.Column(
            "phase",
            sa.Enum(
                "round_robin",
                "play_in",
                "semi",
                "final",
                "bronze",
                name="match_phase",
                create_type=False,
            ),
            nullable=False,
            server_default="round_robin",
        ),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "scheduled",
                "in_progress",
                "paused",
                "pending_review",
                "submitted",
                name="match_state",
                create_type=False,
            ),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("assigned_judge_id", sa.UUID, sa.ForeignKey("judges.id"), nullable=True),
        sa.Column("winner_id", sa.UUID, sa.ForeignKey("participants.id"), nullable=True),
        sa.Column("forfeit_by_id", sa.UUID, sa.ForeignKey("participants.id"), nullable=True),
        sa.Column("current_round", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_sudden_death", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
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
        "ix_matches_last_action_paused",
        "matches",
        ["last_action_at"],
        postgresql_where=sa.text("state = 'paused'"),
    )
    op.create_table(
        "match_rounds",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("match_id", sa.UUID, sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("competitor_a_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("competitor_b_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accumulated_paused_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "state",
            sa.Enum(
                "not_started",
                "running",
                "paused",
                "completed",
                name="round_state",
                create_type=False,
            ),
            nullable=False,
            server_default="not_started",
        ),
    )
    op.create_table(
        "score_events",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("match_id", sa.UUID, sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("competitor_id", sa.UUID, sa.ForeignKey("participants.id"), nullable=False),
        sa.Column("delta", sa.Integer, nullable=False),
        sa.Column("client_event_id", sa.UUID, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_score_events_idempotency",
        "score_events",
        ["match_id", "client_event_id"],
        unique=True,
    )
    op.create_index(
        "ix_score_events_match_round",
        "score_events",
        ["match_id", "round_number", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_score_events_match_round")
    op.drop_index("ix_score_events_idempotency")
    op.drop_table("score_events")
    op.drop_table("match_rounds")
    op.drop_index("ix_matches_last_action_paused")
    op.drop_index("ix_matches_judge_active")
    op.drop_index("ix_matches_division_order")
    op.drop_table("matches")
    op.execute("DROP TYPE round_state")
    op.execute("DROP TYPE match_state")
    op.execute("DROP TYPE match_phase")
