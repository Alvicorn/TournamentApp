"""Round-robin schedule generation.

Pure function — no database access. Call generate_round_robin() with a list
of participant UUIDs; receive back an ordered list of (a, b) match pairs
where every participant faces every other exactly once.

Uses the circle/rotation algorithm:
- Fix slot 0 in place each round.
- Pair slot 0 with slot n-1, slot 1 with slot n-2, etc.
- Rotate slots 1..n-1 rightward for the next round.
- For odd N, pad with a None sentinel; any pair containing None is skipped
  (the corresponding participant rests that round; no bye match is recorded).
"""

from uuid import UUID


def generate_round_robin(participant_ids: list[UUID]) -> list[tuple[UUID, UUID]]:
    """Return all head-to-head pairs in round-robin order.

    Args:
        participant_ids: Unique participant UUIDs. Must be at least 2 for any
            matches to be generated; returns [] for fewer than 2.

    Returns:
        Ordered list of (competitor_a, competitor_b) tuples.
        Total length == N * (N-1) // 2 where N = len(participant_ids).
    """
    n = len(participant_ids)
    if n < 2:
        return []

    # Work with a mutable list; pad to even length with a None sentinel
    slots: list[UUID | None] = list(participant_ids)
    if n % 2 == 1:
        slots.append(None)

    size = len(slots)
    half = size // 2
    matches: list[tuple[UUID, UUID]] = []

    for _ in range(size - 1):  # number of rounds == size - 1
        for i in range(half):
            a = slots[i]
            b = slots[size - 1 - i]
            if a is not None and b is not None:
                matches.append((a, b))
        # Rotate: keep slot 0 fixed, move the last slot to position 1
        slots = [slots[0]] + [slots[-1]] + slots[1:-1]

    return matches
