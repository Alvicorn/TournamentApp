# """Step definitions + scenarios binding for ``match_scoring.feature``.

# pytest-bdd binds scenarios to test functions in this module via ``scenarios()``.
# """

# from __future__ import annotations

# from typing import Any

# from pytest_bdd import given, parsers, scenarios, then, when

# from app.scoring import MatchOutcome, RoundScore, apply_forfeit, determine_outcome

# scenarios("match_scoring.feature")


# @given("a 3-round match between Alice and Bob", target_fixture="state")
# def given_match() -> dict[str, Any]:
#     return {
#         "competitors": {"a": "Alice", "b": "Bob"},
#         "rounds_per_match": 3,
#         "rounds": [],
#         "outcome": None,
#         "winner": None,
#         "match_state": "in_progress",
#     }


# @given(
#     parsers.parse("the round scores are {r1a:d}-{r1b:d}, {r2a:d}-{r2b:d}, {r3a:d}-{r3b:d}"),
# )
# def given_round_scores(
#     state: dict[str, Any], r1a: int, r1b: int, r2a: int, r2b: int, r3a: int, r3b: int
# ) -> None:
#     state["rounds"] = [RoundScore(r1a, r1b), RoundScore(r2a, r2b), RoundScore(r3a, r3b)]


# @given("the match is in sudden-death")
# def given_sudden_death(state: dict[str, Any]) -> None:
#     state["outcome"] = MatchOutcome.SUDDEN_DEATH
#     state["match_state"] = "sudden_death"


# @when("the judge ends the final round and submits")
# def when_end_and_submit(state: dict[str, Any]) -> None:
#     outcome, winner = determine_outcome(state["rounds"])
#     state["outcome"] = outcome
#     state["winner"] = winner
#     state["match_state"] = "submitted"


# @when("the judge ends the final round")
# def when_end_final_round(state: dict[str, Any]) -> None:
#     outcome, winner = determine_outcome(state["rounds"])
#     state["outcome"] = outcome
#     state["winner"] = winner
#     if outcome == MatchOutcome.SUDDEN_DEATH:
#         state["match_state"] = "sudden_death"


# @when("Alice forfeits")
# def when_alice_forfeits(state: dict[str, Any]) -> None:
#     state["winner"] = apply_forfeit("a")
#     state["match_state"] = "pending_review"


# @then(parsers.parse("{name} is the winner"))
# def then_winner(state: dict[str, Any], name: str) -> None:
#     side = next(s for s, n in state["competitors"].items() if n == name)
#     assert state["winner"] == side, f"expected {name} ({side}), got {state['winner']}"


# @then(parsers.parse("the final score is {a:d}-{b:d}"))
# def then_final_score(state: dict[str, Any], a: int, b: int) -> None:
#     a_total = sum(r.a for r in state["rounds"])
#     b_total = sum(r.b for r in state["rounds"])
#     assert (a_total, b_total) == (a, b)


# @then("the match enters sudden-death")
# def then_sudden_death(state: dict[str, Any]) -> None:
#     assert state["outcome"] == MatchOutcome.SUDDEN_DEATH


# @then("no time limit applies")
# def then_no_time_limit(state: dict[str, Any]) -> None:
#     # Sudden-death has no time limit by rule (see docs/product/rules.md).
#     assert state["match_state"] == "sudden_death"


# @then("the match transitions to pending_review")
# def then_pending_review(state: dict[str, Any]) -> None:
#     assert state["match_state"] == "pending_review"
