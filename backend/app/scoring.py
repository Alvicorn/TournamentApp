# """
# Pure scoring helpers — no DB, no FastAPI, no clock.

# These functions encode the rules from ``docs/product/rules.md`` and exist so
# they can be unit-tested cheaply (and BDD-tested via pytest-bdd).
# """

# from dataclasses import dataclass
# from enum import StrEnum


# class MatchOutcome(StrEnum):
#     WINNER = "winner"
#     SUDDEN_DEATH = "sudden_death"


# @dataclass(frozen=True)
# class RoundScore:
#     a: int
#     b: int


# def cumulative(rounds: list[RoundScore]) -> tuple[int, int]:
#     return sum(r.a for r in rounds), sum(r.b for r in rounds)


# def determine_outcome(rounds: list[RoundScore]) -> tuple[MatchOutcome, str | None]:
#     """After the final round, decide winner or sudden-death.

#     Returns (outcome, winner) where winner is "a" / "b" / None.
#     """
#     a_total, b_total = cumulative(rounds)
#     if a_total > b_total:
#         return MatchOutcome.WINNER, "a"
#     if b_total > a_total:
#         return MatchOutcome.WINNER, "b"
#     return MatchOutcome.SUDDEN_DEATH, None


# def apply_forfeit(forfeiter: str) -> str:
#     """Return the winner side given the forfeiter side ("a" or "b")."""
#     if forfeiter not in {"a", "b"}:
#         raise ValueError("forfeiter must be 'a' or 'b'")
#     return "b" if forfeiter == "a" else "a"
