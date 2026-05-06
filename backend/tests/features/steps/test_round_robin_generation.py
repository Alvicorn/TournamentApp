"""BDD step definitions for round_robin_generation.feature."""

from uuid import uuid4

from pytest_bdd import given, scenario, then, when

from app.services.round_robin import generate_round_robin

# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@scenario("round_robin_generation.feature", "Even number of participants")
def test_even(): ...


@scenario("round_robin_generation.feature", "Odd number of participants — no byes recorded")
def test_odd(): ...


@scenario("round_robin_generation.feature", "Minimum of 2 participants")
def test_two(): ...


@scenario("round_robin_generation.feature", "Fewer than 2 participants returns empty")
def test_one(): ...


@scenario("round_robin_generation.feature", "Same input always produces the same output")
def test_deterministic(): ...


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


@given("4 participants", target_fixture="participants")
def four_participants():
    return [uuid4() for _ in range(4)]


@given("5 participants", target_fixture="participants")
def five_participants():
    return [uuid4() for _ in range(5)]


@given("2 participants", target_fixture="participants")
def two_participants():
    return [uuid4() for _ in range(2)]


@given("1 participant", target_fixture="participants")
def one_participant():
    return [uuid4() for _ in range(1)]


@given("6 participants", target_fixture="participants")
def six_participants():
    return [uuid4() for _ in range(6)]


@when("round-robin matches are generated", target_fixture="matches")
def generate(participants):
    return generate_round_robin(participants)


@when("round-robin matches are generated twice with the same input", target_fixture="matches")
def generate_twice(participants):
    first = generate_round_robin(participants)
    second = generate_round_robin(participants)
    return (first, second)


@then("there are 6 matches")
def six_matches(matches):
    assert len(matches) == 6


@then("there are 10 matches")
def ten_matches(matches):
    assert len(matches) == 10


@then("there is 1 match")
def one_match(matches):
    assert len(matches) == 1


@then("there are 0 matches")
def zero_matches(matches):
    assert len(matches) == 0


@then("every pair plays exactly once")
def every_pair_once(matches):
    pairs = {frozenset(m) for m in matches}
    assert len(pairs) == len(matches), "Duplicate pairs found"


@then("both results are identical")
def results_identical(matches):
    first, second = matches
    assert first == second
