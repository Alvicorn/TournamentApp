# Testing Strategy

This app has unusually high correctness requirements (scores affect medals affect people's lives, dramatically). Testing matters more than typical CRUD apps.

## BDD: hybrid adoption

Behavior-driven development is used **selectively** — for tournament rules, scoring, brackets, and standings only. Other concerns (CRUD, auth, concurrency, performance, frontend components) use plain testing tools.

### Where BDD applies
Gherkin feature files in `tests/features/` cover:

1. Match scoring rules (winner determination, sudden-death triggers, forfeit incl. during sudden-death)
2. Standings tie-break order (3-level rule)
3. Bracket generation (semis pairing, bronze/finals construction)
4. Play-in triggers (when ties straddle top 4; ties below top 4 don't trigger play-ins)
5. Late participant additions (allowed in round-robin, blocked after)
6. Match state machine transitions (every legal/illegal transition)
7. Tournament lifecycle transitions
8. Tiny division handling (<2, 2, 3, 4+)
9. Custom field freezing on activation
10. Judge multi-device session invalidation

### Tooling
- **`pytest-bdd`** — Python flavor of Cucumber. Same fixture system as pytest, same CLI, same CI integration.
- Feature files in `tests/features/*.feature`.
- Step definitions in `tests/features/steps/*.py`.
- Reuses the same DB fixtures + factory_boy participants/matches as integration tests.

### Why hybrid (not full BDD)
- Gherkin shines when business rules are complex and need stakeholder review. Tournament rules qualify.
- Gherkin is bureaucracy for CRUD endpoints, concurrency tests, and frontend assertions. Skip it there.
- ~20–30 feature files is the right scope. Resist the urge to BDD everything.

### Example feature file (`tests/features/match_scoring.feature`)

```gherkin
Feature: Match scoring and tie-breaker
  Background:
    Given a 3-round match between Alice and Bob

  Scenario: Higher cumulative score wins
    Given the round scores are 5-3, 4-4, 3-2
    When the judge ends the final round and submits
    Then Alice is the winner
    And the final score is 12-9

  Scenario: Tied final round triggers sudden-death
    Given the round scores are 3-3, 4-4, 5-5
    When the judge ends the final round
    Then the match enters sudden-death
    And no time limit applies
    And the next score event ends the match

  Scenario: Forfeit during sudden-death ends the match
    Given the match is in sudden-death
    When Alice forfeits
    Then Bob is the winner
    And the match transitions to pending_review
```

## Test layers (in order of ROI)

### Layer 1: Backend unit tests (highest ROI)

Cover the business logic that **cannot** be wrong.

**Tooling**: `pytest` + `hypothesis` (property-based) + `pytest-bdd` (rule scenarios).

#### Critical pure functions to test

- **`generate_round_robin(participants)`**
  - Even N: every pair appears exactly once, exactly N−1 rounds.
  - Odd N: every pair appears exactly once, exactly N rounds, exactly one rest per round.
  - 2 competitors: 1 match.
  - 3 competitors: 3 matches.
  - Determinism: same input → same output.
- **`compute_standings(matches)`** *(BDD candidate)*
- **`detect_top_4(standings)`** *(BDD candidate)*
- **`compute_match_winner(rounds, forfeit)`** *(BDD candidate)*
- **`generate_bracket(top_4_seeds)`** *(BDD candidate)*
- **`apply_late_addition(division, participant)`** *(BDD candidate)*
- **Judge code generation**
  - No collisions across 10,000 generations within a tournament.
  - Excludes ambiguous chars (`0/O`, `1/I/L`).
  - Checksum digit catches single-char typos.

#### Hypothesis example
```python
@given(participants=st.lists(participant_strategy, min_size=2, max_size=20, unique=True))
def test_round_robin_every_pair_plays_once(participants):
    matches = generate_round_robin(participants)
    pairs = {frozenset((m.a, m.b)) for m in matches}
    assert len(pairs) == len(participants) * (len(participants) - 1) // 2
```

### Layer 2: Backend integration tests (high ROI)

Test FastAPI routes against a real Postgres. Catches SQL/transaction bugs that unit tests miss.

**Tooling**: `pytest` + `httpx.AsyncClient` + Testcontainers for ephemeral Postgres.

#### Scenarios
- **Full happy path**: tournament → judges/participants → divisions → round-robin → judge claims/scores/submits → bracket → finals/bronze.
- **Concurrency: two judges claim same match** → only one wins, second gets 409.
- **Judge with active match tries to claim another** → rejected with 409.
- **Editing submitted match (round-robin phase)** → standings recalculate; no bracket effect.
- **Editing submitted match (post-round-robin, regenerate=false)** → record updated, bracket untouched.
- **Editing submitted match (post-round-robin, regenerate=true)** → bracket destroyed and rebuilt.
- **Score with duplicate `client_event_id`** → returns same response, doesn't double-count.
- **Score undo** → reverses last event, doesn't affect earlier events.
- **Forfeit during round 2 of 3** → match goes to review, no further rounds played.
- **Sudden death triggers when final round ends tied** → extra round created, no time limit.
- **Auto-release**: paused match with stale `last_action_at` → released, judge unassigned.
- **Auto-release does NOT touch in_progress matches**.
- **Admin reassign of in_progress match** → state becomes paused, new judge assigned.
- **Web push subscription dedupes per device + participant**.
- **Activity log entries created for every admin/judge action**.
- **Custom field spec frozen on tournament transition to active**.

### Layer 3: Frontend component tests (medium ROI)

The judge scoring screen is the only frontend surface where bugs cause real-world damage. Test it thoroughly. Other screens get smoke tests.

**Tooling**: `Vitest` + `React Testing Library` + mocked TanStack Query.

#### Critical scenarios
- Score buttons increment/decrement correctly.
- Submit button disabled until final round has ended.
- Submit confirmation modal blocks accidental clicks.
- Sudden-death banner appears when triggered.
- Forfeit button routes to review screen.
- Timer pauses on pause action and resumes from correct value.
- Undo button reverses last score event.
- Connection-lost banner appears after 5s without successful poll.
- Connection-lost overlay appears after 30s.
- Reconnect re-fetches state and discards local cache.

### Layer 4: End-to-end tests (medium ROI; pick scenarios carefully)

Don't test everything E2E — slow, brittle, expensive. Test critical user journeys only.

**Tooling**: `Playwright`. Run against docker-composed stack with seeded DB.

#### Journeys
1. **Admin sets up a tournament**: create → 4 judges → 8 participants → division → assign → generate round-robin → start.
2. **Judge runs a match**: log in → claim → start → score → end round → score round 2 → submit. Assert `submitted` state with correct winner.
3. **Tied match triggers sudden-death**: identical scores in final round → sudden-death banner → next score wins.
4. **Public spectator subscribes/unsubscribes**: open dashboard → click competitor → subscribe → see "subscribed" → unsubscribe → state clears.
5. **Admin edits a result during round-robin**: edit submitted match → standings reflect new ranking.

#### CI strategy
- E2E runs on `main`, not every PR (too slow).
- Unit + integration on every PR.

### Layer 5: Property-based simulation testing (high ROI, surprisingly cheap)

Build a **headless tournament simulator** that drives the API like a fuzzer:

- Generates a random tournament (3–32 competitors).
- Random rounds per match (1–5).
- Simulates judges claiming, scoring, occasionally forfeiting/pausing.
- Runs the entire tournament to completion.

Asserts invariants:
- Every round-robin match plays exactly once.
- Final standings deterministic given same score sequence.
- Bracket reaches single gold + single bronze winner.
- No participant in two matches simultaneously.
- All match-rounds ended before submit.
- Activity log strictly increasing in `created_at`.
- Total points scored == sum of all score_events deltas.

Run 1,000+ times in CI with different seeds. Catches race conditions and edge cases hand-written tests miss.

**Tooling**: Just Python + `pytest` + the API client. ~200 lines of code.

### Layer 6: Load testing (low ROI for MVP, but easy)

The SSE concurrency limit is the only real perf concern.

**Tooling**: `locust`.

- Open 100 concurrent SSE connections.
- Drive normal admin/judge traffic.
- Monitor CPU, memory, request latency.
- Run once before tournament day, not in CI.

## What we don't bother testing

- Trivial CRUD (FastAPI + Pydantic + SQLAlchemy give 95% correctness for free).
- Tailwind classes / pure rendering (low value).
- Web Push delivery (browser-side, can't reliably test).
- Tutorial-style tests of obvious code.

## CI pipeline

```
On PR:
  ├─ Lint (ruff, eslint, prettier)
  ├─ Type check (mypy, tsc)
  ├─ Unit tests (pytest, vitest)            ← must pass
  ├─ BDD scenarios (pytest-bdd)             ← must pass
  └─ Integration tests (pytest + testcontainers)  ← must pass

On merge to main:
  ├─ All of the above
  ├─ E2E tests (Playwright)                 ← must pass
  ├─ Simulation suite (1,000 random tournaments)  ← must pass
  └─ Deploy to staging

Manual / pre-tournament:
  ├─ Load test (Locust)                     ← sanity check
  └─ Tournament dry run via demo mode
```

## Test data fixtures

- `fixtures/tournaments.py` — common tournament shapes (small, medium, large, edge cases).
- `fixtures/scenarios.py` — full scenarios like "tied round-robin", "forfeit early", "all-tied playoff".
- Use `pytest` fixtures with appropriate scopes.

## Coverage targets

- Backend: aim for ~85% line coverage. **Higher (~95%+) on the pure-logic modules** (scoring, standings, bracket).
- Frontend: aim for ~70% line coverage; **judge scoring screen ~90%+**.
- Don't chase 100% coverage; chase the right tests in the right places.
