"""Import all ORM models so Base.metadata is fully populated.

Any module that calls Base.metadata.create_all() or imports Base for Alembic
must import this package first.
"""

from app.models.activity_log import ActivityLog, ActorType
from app.models.backup import Backup, BackupStatus, BackupTrigger
from app.models.base import Base
from app.models.division import Division, DivisionState
from app.models.judge import Judge
from app.models.match import Match, MatchPhase, MatchRound, MatchState, RoundState, ScoreEvent
from app.models.participant import Participant
from app.models.tournament import LifecycleState, Tournament

__all__ = [
    "Base",
    "Tournament",
    "LifecycleState",
    "Judge",
    "Participant",
    "Division",
    "DivisionState",
    "Match",
    "MatchRound",
    "ScoreEvent",
    "MatchPhase",
    "MatchState",
    "RoundState",
    "ActivityLog",
    "ActorType",
    "Backup",
    "BackupTrigger",
    "BackupStatus",
]
