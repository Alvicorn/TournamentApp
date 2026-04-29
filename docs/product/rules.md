# Tournament Rules & Logic

## Match flow

- A match consists of N rounds (admin-configured).
- Each round has a fixed time limit (admin-configured).
- Judge increments/decrements points (`+1` / `-1`) per competitor during the active round.
- A match ends when the final round ends.
- **Winner**: highest cumulative score across all rounds.

## Tie-breaker (within a single match)

- If cumulative scores are tied at the end of the final round, an **extra sudden-death round** is added with **no time limit**.
- The next point scored wins.
- UI clearly indicates sudden death is active (see [`frontend.md`](../engineering/frontend.md#sudden-death-visual)).

## Forfeit

- Judge can mark either competitor as forfeit. This terminates the match immediately and routes to the review screen before submission.

## Standings (within a division)

Competitors are ranked by, in order:

1. Number of wins
2. Total points scored by the competitor
3. Total points scored against by opponents (lower is better)

### Ties below the top 4
Play-ins are run **only** when ties straddle the top-4 cutoff (i.e., when ties affect who enters the bracket). Ties for 5th, 6th, or any lower position are **displayed as ties** in the standings without play-in resolution. The bracket determines medals; lower placements are a leaderboard concern only.

### Result display format
- Standard: `"Alice def. Bob 5-3 in 3 rounds"`
- Sudden-death: `"Alice def. Bob 6-5 in sudden-death"`
- Forfeit: `"Alice def. Bob (forfeit)"`

## Forfeit during sudden-death

Forfeit is allowed at any point during a match, including sudden-death. The behavior is the same as a regular forfeit: match ends, opponent wins, judge routed to review. See [`correctness.md`](../engineering/correctness.md#forfeit-during-sudden-death).

## Round-robin generation

- Every competitor faces every other competitor exactly once.
- For odd N, one competitor rests per round (no bye match recorded — they simply don't play that round).
- Match order generated automatically. Admin and judges can reorder.

## Parallel matches within a division

- During **round-robin**, multiple matches can run simultaneously within a division as long as no competitor is in two matches at once.
- During **play-ins, semis, finals, and bronze**, only **one match at a time** per division.
- Server enforces these rules; UI surfaces conflicts. See [`correctness.md`](../engineering/correctness.md#parallel-matches-within-a-division).

## Late participant additions

- Admin can add participants to a division during `round_robin` phase.
- New participants get matches **appended** against every existing competitor — previously-played matches are not invalidated.
- Once a division has advanced past round-robin (`play_ins`, `semis`, `finals`), late additions are blocked.
- See [`correctness.md`](../engineering/correctness.md#late-participant-additions).

## Bracket after round-robin

- If standings unambiguously determine the top 4: skip play-ins, advance directly.
- If ties straddle the top-4 cutoff: run **single-elimination play-in matches** between only the tied competitors until exactly 4 remain.
- Top 4 are seeded by final standings (1st, 2nd, 3rd, 4th).
- **Semis**: 1v4 and 2v3.
- **Finals**: winners of semis (gold medal match).
- **Bronze match**: losers of semis.

### Play-in tie resolution

Play-in matches use the same scoring rules as regular matches, including sudden-death. Sudden-death guarantees resolution — there is no scenario where a play-in cannot determine a winner.

## Tiny divisions

| Competitors | Behavior |
|---|---|
| < 2 | Division can't run; admin sees a warning |
| 2 | Single match → gold/silver, no bronze |
| 3 | Round-robin only; standings determine all 3 medals |
| 4+ | Round-robin → (play-ins if needed) → semis → finals + bronze |

## State machines

### Match state machine

```
scheduled → in_progress → paused ↔ in_progress → pending_review → submitted
                                                         ↑
                                          (forfeit jumps here)
```

- Admin can edit `submitted` matches; judges cannot.
- Edits to submitted matches have tiered consequences — see [`correctness.md`](../engineering/correctness.md#editing-submitted-matches).

### Division state machine

```
setup → round_robin → play_ins → semis → finals → completed
                ↓        ↓        ↓        ↓
              paused   paused   paused   paused
```

- Admin can pause/resume a division at any point.
- A paused division's matches cannot be started by judges, but already-running matches can finish.

### Tournament lifecycle

```
setup → active → completed
```

- Participants/judges/divisions can only be **created or removed** during `setup`.
- During `active`, participants can still be edited (name corrections), but not removed.
- Admin can force back to `setup` if needed (with hard warning).

## Custom participant fields

- Defined at tournament initialization as `[{key, label, type, required}]`.
- **Spec is frozen** when tournament transitions out of `setup`.
- While in `setup`, edits to the spec back-fill defaults / null on existing participants with a UI warning.

## Demo / dry-run mode

- Tournaments can be flagged `is_demo = true`.
- Demo tournaments are excluded from public dashboard and slideshow.
- Demo tournaments can be **reset** at any time, restoring them to fresh `setup` state.
- Used for staff training and pre-event rehearsal.
