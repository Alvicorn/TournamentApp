"""Hypothesis property-based tests for round_robin.generate_round_robin."""

from uuid import UUID, uuid4

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.round_robin import generate_round_robin


def _unique_uuids(min_size: int, max_size: int) -> st.SearchStrategy[list[UUID]]:
    return st.lists(
        st.uuids().map(lambda u: UUID(str(u))),
        min_size=min_size,
        max_size=max_size,
        unique=True,
    )


@given(_unique_uuids(2, 20))
@settings(max_examples=200)
def test_every_pair_plays_exactly_once(participant_ids: list[UUID]) -> None:
    matches = generate_round_robin(participant_ids)
    pairs = {frozenset(m) for m in matches}
    n = len(participant_ids)
    expected = n * (n - 1) // 2
    assert len(pairs) == expected, f"Expected {expected} unique pairs, got {len(pairs)}"
    assert len(matches) == expected, "Duplicate matches generated"


@given(_unique_uuids(2, 20))
@settings(max_examples=200)
def test_match_count_formula(participant_ids: list[UUID]) -> None:
    matches = generate_round_robin(participant_ids)
    n = len(participant_ids)
    assert len(matches) == n * (n - 1) // 2


@given(_unique_uuids(2, 20))
@settings(max_examples=100)
def test_deterministic(participant_ids: list[UUID]) -> None:
    assert generate_round_robin(participant_ids) == generate_round_robin(participant_ids)


@given(_unique_uuids(1, 1))
def test_single_participant_returns_empty(participant_ids: list[UUID]) -> None:
    assert generate_round_robin(participant_ids) == []


def test_two_participants() -> None:
    a, b = uuid4(), uuid4()
    matches = generate_round_robin([a, b])
    assert len(matches) == 1
    assert frozenset(matches[0]) == frozenset({a, b})
