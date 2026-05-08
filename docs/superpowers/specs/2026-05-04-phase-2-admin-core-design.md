# Phase 2 — Admin Core: Design Spec

**Date:** 2026-05-04
**Status:** Approved
**Approach:** A — Domain-organized backend, polling activity feed, pg_dump backups

---

## Scope

Full-stack implementation (backend + frontend together), tests included, manual + automated backups included.

Phase 2 features from backlog:

1. Tournament setup with custom fields + IANA time zone capture
2. Demo / dry-run mode toggle + reset endpoint
3. Judge CRUD + code generation (with checksum)
4. Participant CRUD with custom field rendering
5. Late participant addition (append matches; block after bracket starts)
6. Division CRUD + participant assignment/movement
7. Round-robin generation (even/odd, no bye matches)
8. Match listing + manual reorder
9. Match result editing (round-robin phase only)
10. Activity log writes
11. Activity feed view (admin home + dedicated page)
12. Manual backup snapshot button + automated hourly during active

---

## Section 1: Backend structure & data models

### Directory layout

```
backend/app/
  models/
    tournament.py
    judge.py
    participant.py
    division.py
    match.py          # also covers match_rounds + score_events
    activity_log.py
    backup.py
  schemas/
    tournament.py
    judge.py
    participant.py
    division.py
    match.py
    activity_log.py
    backup.py
  services/
    tournament.py
    judge.py
    participant.py
    division.py
    match.py
    round_robin.py    # pure function, no DB access
    activity_log.py
    backup.py
  routes/             # thin FastAPI routers
    tournaments.py
    judges.py
    participants.py
    divisions.py
    matches.py
    activity.py
    backups.py
```

### Migrations (Alembic, in FK-dependency order)

| # | File | Tables created |
|---|---|---|
| 0002 | `add_tournaments` | `tournaments` |
| 0003 | `add_judges` | `judges` |
| 0004 | `add_participants` | `participants` |
| 0005 | `add_divisions` | `divisions` |
| 0006 | `add_matches` | `matches`, `match_rounds`, `score_events` |
| 0007 | `add_activity_log` | `activity_log` |
| 0008 | `add_backups` | `backups` |

### Model conventions

- UUID PKs via `uuid_pk()` from `base.py`.
- All timestamps: `TIMESTAMPTZ` with `server_default=func.now()`. No Python `datetime.now()`.
- All deletes: soft delete via `SoftDeleteMixin.deleted_at`.
- Enums as Python `enum.Enum` + SQLAlchemy `Enum` column type.
- JSON columns (`custom_participant_fields`, `custom_fields`, `metadata`) use SQLAlchemy `JSONB` dialect type.

### Key model notes

**`tournaments`**: `lifecycle_state` enum: `setup | active | completed`. `custom_participant_fields`: `JSONB` list of `{key, label, type, required}`. `is_demo: bool`. Service-layer constraint: only one non-demo, non-completed, non-deleted tournament at a time.

**`judges`**: `code` is 8-char uppercase (`XXXXXXXX`), unique per `(tournament_id, code)`. `current_session_jti` nullable UUID (Phase 3 wires it; column added now).

**`participants`**: `division_id` nullable FK. `custom_fields`: `JSONB`. `is_withdrawn: bool` (distinct from soft delete — withdrawn keeps history).

**`divisions`**: `state` enum: `setup | round_robin | play_ins | semis | finals | completed | paused`. `paused_reason` nullable text.

**`matches`**: `phase` enum: `round_robin | play_in | semi | final | bronze`. `state` enum: `scheduled | in_progress | paused | pending_review | submitted`. `order_index: int` for queue ordering.

**`match_rounds`**: `state` enum: `not_started | running | paused | completed`. `accumulated_paused_seconds: int`.

**`score_events`**: append-only. Unique index on `(match_id, client_event_id)` for idempotency.

**`activity_log`**: `actor_type` enum: `admin | judge | system`. No foreign key on `actor_id` (denormalized `actor_display_name` for fast display).

**`backups`**: `triggered_by` enum: `manual | pre_action | hourly`. `s3_key: text`. `size_bytes: int nullable`. `status` enum: `pending | complete | failed`. `pre_action_description: text nullable` (e.g. "generate-round-robin for division Heavyweight").

### Key indexes (per backend.md)

```sql
CREATE INDEX ON matches (division_id, order_index) WHERE deleted_at IS NULL;
CREATE INDEX ON matches (assigned_judge_id) WHERE state = 'in_progress' AND deleted_at IS NULL;
CREATE INDEX ON matches (last_action_at) WHERE state = 'paused';
CREATE INDEX ON participants (division_id, is_withdrawn) WHERE deleted_at IS NULL;
CREATE INDEX ON activity_log (tournament_id, created_at DESC);
CREATE INDEX ON score_events (match_id, round_number, created_at DESC);
```

---

## Section 2: API layer (routes + services)

**Pattern:** Routes are thin — validate auth dependency → call service function → return Pydantic response schema. Services own all DB access, constraint checks, activity log writes, and snapshot triggers. No business logic in route handlers.

### Tournaments

- `POST /api/v1/tournaments` — create; captures `time_zone` from body (client sends `Intl.DateTimeFormat().resolvedOptions().timeZone`); enforces one-active-non-demo constraint.
- `GET /api/v1/tournaments/active` — returns current non-demo, non-completed tournament or 404.
- `PATCH /api/v1/tournaments/{id}` — edit config; rejects `custom_participant_fields` mutations when `lifecycle_state != 'setup'` → 409 `CUSTOM_FIELDS_FROZEN`.
- `POST /api/v1/tournaments/{id}/lifecycle` — body: `{state: "active" | "completed"}`; triggers pre-action snapshot; freezes custom fields on `active`.
- `POST /api/v1/tournaments/{id}/reset` — demo-only; soft-deletes all child records in reverse FK order; resets `lifecycle_state` to `setup`; clears `custom_participant_fields`.
- `DELETE /api/v1/tournaments/{id}` — soft delete; only demo or completed tournaments.

### Judges

- `POST /api/v1/tournaments/{id}/judges` — generates code via `codes.py` with collision retry loop; returns `{id, name, code, created_at}`.
- `GET /api/v1/tournaments/{id}/judges` — list, excludes soft-deleted.
- `DELETE /api/v1/judges/{id}` — soft delete; if judge has active match: pauses it, nulls `assigned_judge_id`, writes activity log `judge.removed_active`; sets `current_session_jti = null`.

### Participants

- `POST /api/v1/tournaments/{id}/participants` — validates required custom fields are present.
- `GET /api/v1/tournaments/{id}/participants` — list with `division_id` included.
- `PATCH /api/v1/participants/{id}` — name/custom field edit; blocked if tournament `completed`.
- `DELETE /api/v1/participants/{id}` — if matches exist: `is_withdrawn = true`; otherwise soft delete.

### Divisions

- `POST /api/v1/tournaments/{id}/divisions`
- `GET /api/v1/tournaments/{id}/divisions`
- `PATCH /api/v1/divisions/{id}` — rename or pause/resume.
- `POST /api/v1/divisions/{id}/assign-participant` — sets `participants.division_id`. Guard: participant must have `division_id = null` (a participant can only belong to one division at a time) → else 409 `ALREADY_IN_DIVISION`. If division state is `round_robin`: triggers late-addition path (generates matches, appends with next `order_index`, writes `participant.added_late` activity log). If state is `play_ins` or beyond: 409 `DIVISION_ADVANCED`.
- `POST /api/v1/divisions/{id}/move-participant` — body: `{participant_id, target_division_id}`; only allowed when both divisions are in `setup` state.
- `POST /api/v1/divisions/{id}/generate-round-robin` — pre-action snapshot → calls `round_robin.generate()` → bulk-inserts matches → transitions division to `round_robin` → writes activity log.

### Matches

- `GET /api/v1/divisions/{id}/matches` — ordered by `order_index`.
- `POST /api/v1/divisions/{id}/reorder-matches` — body: `{ordered_match_ids: [...]}`; reassigns `order_index` 0…n sequentially.
- `POST /api/v1/matches/{id}/edit-result` — Phase 2: round-robin only. Body: `{round_scores: [{round_number, competitor_a_score, competitor_b_score}]}`. Pre-action snapshot → update `match_rounds` → recompute `winner_id` → write `match.result_edited` activity log with old/new values in `metadata`. Does not touch `score_events`.

### Activity log

- `GET /api/v1/tournaments/{id}/activity` — query params: `since` (ISO timestamp, optional), `division_id` (optional), `limit` (default 50, max 200).

### Backups

- `GET /api/v1/tournaments/{id}/backups` — list metadata rows, descending `created_at`.
- `POST /api/v1/tournaments/{id}/backups` — manual trigger; spawns `asyncio` background task; returns backup row with `status: pending` immediately.

### Pre-action snapshot trigger points

Automatic snapshots fired before: `generate-round-robin`, `lifecycle` transition, `edit-result`, late participant addition (via `assign-participant` on active division). The backup service runs `pg_dump` subprocess → gzip → upload to S3 via `boto3` → update backup row to `complete` (or `failed` on error).

### Hourly backup job

Registered via FastAPI's lifespan context manager (`@asynccontextmanager` passed to `FastAPI(lifespan=...)`). Spawns an `asyncio` background task that sleeps 3600s, wakes, checks for an active non-demo tournament, fires a snapshot. Stops automatically when tournament reaches `completed`. (`app.on_event` is deprecated in modern FastAPI.)

### Activity log writes

Every significant service action writes to `activity_log`. Action verb-phrases:

| Action | When |
|---|---|
| `tournament.created` | Tournament POST |
| `tournament.updated` | Tournament PATCH |
| `tournament.activated` | Lifecycle → active |
| `tournament.completed` | Lifecycle → completed |
| `tournament.reset` | Demo reset |
| `judge.added` | Judge POST |
| `judge.removed` | Judge DELETE |
| `judge.removed_active` | Judge DELETE with active match |
| `participant.added` | Participant POST |
| `participant.updated` | Participant PATCH |
| `participant.withdrawn` | Participant DELETE with matches |
| `participant.added_late` | Late addition during round_robin |
| `division.created` | Division POST |
| `division.paused` | Division PATCH pause |
| `division.resumed` | Division PATCH resume |
| `division.round_robin_generated` | generate-round-robin |
| `match.result_edited` | edit-result |
| `match.reordered` | reorder-matches |
| `backup.created` | Any backup trigger |

---

## Section 3: Frontend pages

**Shared patterns:**
- Server state via TanStack Query; UI state via local `useState`.
- Mutations call `apiFetch` with admin JWT from `useAuthStore`.
- `invalidateQueries` after every mutation.
- Error toasts via `useNotificationsStore`.
- Loading skeletons on initial fetch.
- Empty states per `frontend.md` spec.
- All forms client-side validated before submit.

### AdminHome (`/admin`)

- Tournament status card: name, date, lifecycle badge, demo badge, lifecycle action button ("Activate" / "Complete").
- Activity feed panel: last 20 entries, polls `GET /activity?limit=20` every 5s via `refetchInterval`. Each row: actor display name, action, description, relative timestamp.
- If no active tournament: "Get started by creating your first tournament." CTA linking to `/admin/setup`.
- Unclaimed match alert banner: shown when >3 round-robin matches unclaimed and tournament active >15 min. In Phase 2, `GET /api/v1/tournaments/{id}/unclaimed-summary` is a stub that always returns `{unclaimed_count: 0, division_count: 0}` so the banner never fires; Phase 3 wires the real query.

### AdminSetup (`/admin/setup`)

- Two modes: create-new (no active tournament) and edit-existing.
- Fields: name, competition date, rounds per match, round length (seconds), slideshow duration, demo mode toggle, judge auto-release seconds.
- IANA timezone captured silently via `Intl.DateTimeFormat().resolvedOptions().timeZone` on submit — no UI picker.
- Custom field builder: list of rows `{key, label, type (text|number|select), required}`. "Add field" appends blank row. Delete button per row. Read-only when tournament is `active`.
- On save: POST (create) or PATCH (edit).

### AdminJudges (`/admin/judges`)

- Dense table: name, code (monospace, formatted `XXXX-XXXX1`, copy-to-clipboard button), created date, delete action.
- "Add Judge" button: inline form with name input.
- Delete: confirmation modal; warns "This judge has an active match — it will be paused." if applicable.

### AdminParticipants (`/admin/participants`)

- Table columns: name, division (dropdown in setup, read-only after), each custom field column, withdrawn badge, edit/delete actions.
- "Add Participant": inline form with name + all custom fields.
- Edit: inline row-edit.
- Delete: modal warns "Participant will be marked withdrawn" if matches exist.

### AdminDivisions (`/admin/divisions`)

- Division cards: name, state badge, participant count, match count, actions (view, rename, pause/resume, delete).
- "New Division" inline form at top.

### AdminDivisionDetail (`/admin/divisions/:id`)

Three panels:

**Participants panel:**
- List of assigned participants. "Remove from division" (setup only) and "Move to division" (setup only) actions.
- "Assign participant" dropdown (participants not yet in a division).
- "Add late participant" button visible only when division state is `round_robin`.

**Matches panel:**
- Table ordered by `order_index`: competitors, state badge, assigned judge, result summary.
- Up/down arrow buttons for reorder (no drag library).
- "Generate Round-Robin" button — disabled after state is `round_robin`; shows count of matches that will be created.
- "Edit Result" inline for `submitted` matches in `round_robin` phase — opens score-per-round form.

**Division controls:**
- State display, pause/resume button.

### AdminActivity (`/admin/activity`)

- Full log with filter bar: division picker, actor type filter, free-text search on description.
- Polls every 5s.
- Paginated (load-more button, not infinite scroll).

### AdminBackups (`/admin/backups`)

- Table: triggered by, pre-action description, timestamp, size, status badge (pending/complete/failed).
- "Snapshot Now" button — calls `POST /backups`, adds optimistic pending row, refreshes on next poll.

---

## Section 4: Round-robin algorithm & key business logic

### Round-robin generation (`services/round_robin.py`)

Pure function — no DB access:

```python
def generate_round_robin(participant_ids: list[UUID]) -> list[tuple[UUID, UUID]]:
    """
    Circle/rotation algorithm. Returns ordered list of (competitor_a, competitor_b) pairs.
    For odd N, pads with None sentinel; any pair containing None is dropped.
    Total matches: N*(N-1)//2. No bye match recorded.
    """
```

Guarantees:
- Every pair appears exactly once.
- Even N: N−1 rounds. Odd N: N rounds, one participant rests per round.
- Deterministic: same input → same output.
- No bye matches recorded (odd N resting participant simply has no match that round).

Service wrapper: fetch active non-withdrawn participants → call pure function → bulk-insert `Match` rows with sequential `order_index` → transition division state → pre-action snapshot → activity log.

### Custom field freezing

PATCH `/tournaments/{id}` rejects any body containing `custom_participant_fields` when `lifecycle_state != 'setup'` → 409 `CUSTOM_FIELDS_FROZEN`. Lifecycle endpoint unfreezes on force-back-to-setup (not in Phase 2 scope but field check is symmetric).

### Match result editing (round-robin only)

Service steps:
1. Guard: division state must be `round_robin` → else 409 `DIVISION_ADVANCED`.
2. Guard: match state must be `submitted` → else 409.
3. Pre-action snapshot.
4. Capture old `match_rounds` scores and `winner_id` for activity log metadata.
5. Update each `match_rounds` row with new scores.
6. Recompute `winner_id`: sum scores across all rounds; higher cumulative total wins. (Admin-supplied scores are explicit; no sudden-death logic needed here.)
7. Write `match.result_edited` activity log entry.
8. `score_events` untouched — preserved as audit trail.

### Late participant addition

`assign-participant` service branches on division state:
- `setup`: simple `participants.division_id = division.id`.
- `round_robin`: generate new `Match` rows (late participant vs every non-withdrawn existing participant); append with `next_order_index = max(order_index) + 1, +2, ...`; write `participant.added_late` activity log.
- `play_ins` / `semis` / `finals` / `completed`: 409 `DIVISION_ADVANCED`.

### Tournament reset (demo only)

Soft-delete in reverse FK order: `score_events` → `match_rounds` → `matches` → `activity_log` → `participants` → `judges` → `divisions`. Then set `tournament.lifecycle_state = 'setup'`, clear `custom_participant_fields = []`. Guard: 409 if `is_demo = false`.

### Judge code generation

Existing `codes.py` provides `generate_judge_code()` and `is_valid_judge_code()`. Service wraps in retry loop: generate → query `(tournament_id, code)` for uniqueness → retry on collision. Expected collision rate is negligible.

### Pre-action snapshot trigger

The backup service runs synchronously with the request but offloads the actual dump via FastAPI's `BackgroundTasks` dependency (passed through from the route handler — the service accepts it as a parameter). This avoids `asyncio.create_task` from a sync context, which is incompatible with the sync SQLAlchemy session model.

```python
def trigger_pre_action_snapshot(tournament_id, description: str, db, background_tasks: BackgroundTasks):
    backup_row = Backup(tournament_id=tournament_id, triggered_by="pre_action",
                        pre_action_description=description, status="pending")
    db.add(backup_row)
    db.commit()
    background_tasks.add_task(run_backup, backup_row.id)
```

`run_backup`: subprocess `pg_dump` → gzip → `boto3` S3 upload → update row to `complete` (opens its own DB session).

---

## Section 5: Testing strategy

### BDD feature files (`tests/features/`)

| File | Key scenarios |
|---|---|
| `round_robin_generation.feature` | Even N: every pair once, N−1 rounds. Odd N: every pair once, N rounds, no byes. 2 participants: 1 match. Determinism. |
| `tournament_lifecycle.feature` | setup→active freezes fields. active→completed blocks writes. Demo reset restores setup. |
| `custom_field_freezing.feature` | Edit rejected when active. Add field back-fills null. Remove field drops values. |
| `late_participant_addition.feature` | Allowed in `round_robin` → N new matches. Blocked in `play_ins` → 409. |
| `match_state_machine.feature` | Every legal transition succeeds. Every illegal transition returns correct error. Edit-result only on submitted matches in round_robin. |

### Hypothesis property tests (`tests/test_round_robin.py`)

- Every pair plays exactly once (for any 2–20 participants).
- No participant appears in two matches in the same round.
- Match count = `N*(N-1)//2` for both even and odd N.

### Integration tests (FastAPI test client + Testcontainers Postgres)

- Full happy path: tournament → judges → participants → division → assign → generate-round-robin → reorder → edit-result → activity log entries present.
- 500 code generations for one tournament → all unique, all pass checksum, no ambiguous chars.
- Late addition mid-round-robin → correct number of new matches appended.
- Edit-result blocked when division state is not `round_robin` → 409.
- Demo reset → all child rows soft-deleted, lifecycle back to `setup`.
- Custom field freeze → PATCH rejected with 409.
- Delete judge with active match → match paused, `assigned_judge_id` null, activity log entry.
- Delete participant with matches → `is_withdrawn = true`, record kept.

### Frontend component tests (Vitest + React Testing Library)

- `AdminSetup`: custom field builder adds/removes rows; fields disabled when tournament active.
- `AdminJudges`: code formatted as `XXXX-XXXX1`; delete modal warns on active match.
- `AdminDivisionDetail`: generate button disabled post-generation; late-add button visible only in `round_robin` state; edit-result form opens for submitted matches.
- `AdminActivity`: entries render; division filter narrows results.

---

## Implementation order

**All 8 Alembic migrations (0002–0008) are written and applied first**, before any slice implementation begins. This ensures the `activity_log` and `backups` tables exist from the start and services can write to them from slice 1. The slices below refer to route/service/frontend implementation order, not migration order.

Slices 1–6 write activity log entries as they go (table exists); slice 7 adds the frontend feed and fills any gaps in log coverage.

1. **Tournament CRUD** — models, schemas, service, routes, AdminSetup page, AdminHome stub.
2. **Judge CRUD** — service (with code gen), routes, AdminJudges page.
3. **Participant CRUD** — service, routes, AdminParticipants page.
4. **Division CRUD** — service, routes, AdminDivisions page, AdminDivisionDetail skeleton.
5. **Round-robin generation** — `round_robin.py` pure function + BDD/Hypothesis tests, generate endpoint, match list + reorder in AdminDivisionDetail.
6. **Match result editing** — edit-result endpoint + frontend inline form.
7. **Activity log frontend** — activity log writes audited/filled across all services, AdminHome feed + AdminActivity page.
8. **Backups** — backup service (pg_dump + S3), endpoints, AdminBackups page.
