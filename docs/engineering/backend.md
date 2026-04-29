# Backend

## Stack

- **Python** + **FastAPI**
- **SQLAlchemy** (ORM, sync mode for simplicity in MVP)
- **Alembic** (migrations)
- **Supabase Postgres** (database; accessed via SQLAlchemy)
- **Supabase Auth** for admin login (FastAPI verifies JWTs)
- Self-signed JWTs for judge sessions (HS256, server-side secret)
- **Redis** for SSE pub/sub fan-out across uvicorn workers
- **uvicorn** with `--workers N` (N = CPU count)

## Data model

All PKs are UUIDs unless noted. Timestamps are `TIMESTAMPTZ`. **All deletes are soft deletes** via `deleted_at` column.

### `tournaments`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| name | text | |
| competition_date | date | |
| time_zone | text | IANA TZ (e.g., `America/Vancouver`); captured from admin browser at creation |
| rounds_per_match | int | |
| round_length_seconds | int | |
| slideshow_slide_seconds | int | Global slideshow timing |
| lifecycle_state | enum | `setup \| active \| completed` |
| custom_participant_fields | jsonb | `[{key, label, type, required}]`; frozen on `active` |
| is_demo | bool | Excludes from public view; allows reset |
| judge_auto_release_seconds | int | Default 600; auto-release stale paused matches |
| created_at, updated_at, deleted_at | timestamptz | |

> Service-layer constraint: only one tournament with `lifecycle_state != completed` AND `deleted_at IS NULL` AND `is_demo = false` at a time.

### `judges`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| tournament_id | uuid FK | |
| name | text | |
| code | text | 8-char alphanumeric uppercase + checksum digit (Luhn-mod-32) |
| current_session_jti | uuid nullable | Tracks active JWT for single-device binding; null when logged out |
| is_active | bool | |
| created_at, deleted_at | timestamptz | |

> Unique index: `(tournament_id, code)` — codes are tournament-scoped, not globally unique.

### `participants`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| tournament_id | uuid FK | |
| division_id | uuid FK nullable | |
| name | text | |
| custom_fields | jsonb | Values per tournament's spec |
| is_withdrawn | bool | Distinct from soft delete: withdrawn but historical record kept |
| created_at, deleted_at | timestamptz | |

### `divisions`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| tournament_id | uuid FK | |
| name | text | |
| state | enum | `setup \| round_robin \| play_ins \| semis \| finals \| completed \| paused` |
| paused_reason | text nullable | |
| created_at, deleted_at | timestamptz | |

### `matches`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| division_id | uuid FK | |
| competitor_a_id | uuid FK→participants | |
| competitor_b_id | uuid FK→participants | |
| phase | enum | `round_robin \| play_in \| semi \| final \| bronze` |
| order_index | int | Queue ordering within division |
| state | enum | `scheduled \| in_progress \| paused \| pending_review \| submitted` |
| assigned_judge_id | uuid FK nullable | |
| winner_id | uuid FK nullable | |
| forfeit_by_id | uuid FK nullable | |
| current_round | int | 1-indexed |
| is_sudden_death | bool | |
| started_at, submitted_at, last_action_at | timestamptz | `last_action_at` powers auto-release |
| deleted_at | timestamptz | |

### `match_rounds`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| match_id | uuid FK | |
| round_number | int | |
| competitor_a_score | int | |
| competitor_b_score | int | |
| started_at, ended_at | timestamptz | Server-authoritative timestamps |
| accumulated_paused_seconds | int | For correct elapsed-time computation |
| state | enum | `not_started \| running \| paused \| completed` |

### `score_events`
Append-only log enabling undo and idempotency.

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| match_id | uuid FK | |
| round_number | int | |
| competitor_id | uuid FK | |
| delta | int | `+1` or `-1` |
| client_event_id | uuid | Client-generated, deduped server-side |
| created_at | timestamptz | |
| undone_at | timestamptz nullable | |

> Unique index: `(match_id, client_event_id)` for idempotency.

### `subscriptions`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| device_id | uuid | From localStorage |
| participant_id | uuid FK nullable | |
| tournament_wide | bool | |
| web_push_endpoint | jsonb nullable | VAPID subscription object |
| created_at, deleted_at | timestamptz | |

> Constraint: `(participant_id IS NOT NULL) XOR (tournament_wide = true)`.

### `broadcasts`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| tournament_id | uuid FK | |
| message | text | |
| target_subscribers | bool | If true, dispatch to subscribers (toast + push) |
| target_public_dashboard | bool | If true, show as banner on public dashboard |
| sent_at | timestamptz | |
| sent_by | uuid | Admin user id |

> Constraint: `target_subscribers OR target_public_dashboard` (must hit at least one channel).

### `activity_log`
Surfaced in admin UI as a real-time event feed (see [`frontend.md`](frontend.md)).

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| tournament_id | uuid FK | |
| division_id | uuid FK nullable | For filtering by division |
| actor_type | enum | `admin \| judge \| system` |
| actor_id | uuid nullable | Null for `system` (e.g., auto-release) |
| actor_display_name | text | Denormalized for fast display |
| action | text | Short verb-phrase, e.g., `match.submitted` |
| description | text | Human-readable, e.g., "Judge Maria submitted Match 12 — Alice def. Bob 5-3" |
| metadata | jsonb | |
| created_at | timestamptz | |

> **Granularity rule**: individual score events do NOT write to `activity_log` (they live in `score_events` table). Only meaningful state transitions log: claim, start, pause, end_round, forfeit, submit, edit_result, reassign_judge, late participant addition, etc. This keeps the feed scannable.

### Key indexes
- `matches (division_id, order_index) WHERE deleted_at IS NULL`
- `matches (assigned_judge_id) WHERE state = 'in_progress' AND deleted_at IS NULL`
- `matches (last_action_at) WHERE state = 'paused'` — auto-release scan
- `participants (division_id, is_withdrawn) WHERE deleted_at IS NULL`
- `subscriptions (participant_id) WHERE deleted_at IS NULL`
- `subscriptions (tournament_wide) WHERE deleted_at IS NULL`
- `activity_log (tournament_id, created_at DESC)`
- `score_events (match_id, round_number, created_at DESC)`

## API surface

All routes prefixed `/api/v1`. JSON bodies. JWT in `Authorization: Bearer ...` where required.

### Auth
- `POST /auth/admin/login` — proxies to Supabase, returns JWT
- `POST /auth/judge/login` — body: `{tournament_id, code}`, returns FastAPI-signed judge JWT
- Public: no auth; sends `X-Device-Id` header (UUID generated client-side)

### Admin (require admin JWT)

**Tournament**
- `POST /tournaments` — create + initialize (supports `is_demo: true`); captures admin's IANA time zone
- `GET /tournaments/active`
- `PATCH /tournaments/{id}` — edit config
- `POST /tournaments/{id}/lifecycle` — transition state
- `DELETE /tournaments/{id}` — soft delete; only allowed on demo tournaments or completed tournaments

**Judges**
- `POST /tournaments/{id}/judges` — returns generated code
- `DELETE /judges/{id}` — soft delete
- `GET /tournaments/{id}/judges`

**Participants**
- `POST /tournaments/{id}/participants`
- `PATCH /participants/{id}`
- `DELETE /participants/{id}` — soft delete; `is_withdrawn = true` if matches exist
- `GET /tournaments/{id}/participants`

**Divisions**
- `POST /tournaments/{id}/divisions`
- `PATCH /divisions/{id}` — rename, pause/resume
- `POST /divisions/{id}/assign-participant` — body: `{participant_id}`
- `POST /divisions/{id}/move-participant` — body: `{participant_id, target_division_id}`
- `POST /divisions/{id}/generate-round-robin`
- `POST /divisions/{id}/advance-bracket` — computes seedings, creates play-ins/semis/finals/bronze

**Matches**
- `GET /divisions/{id}/matches`
- `PATCH /matches/{id}` — edit results, reorder. Returns warning payload if division has advanced past round-robin.
- `POST /matches/{id}/edit-result` — body: `{round_scores: [...], regenerate_bracket: bool}`. See [`correctness.md`](correctness.md#editing-submitted-matches).
- `POST /divisions/{id}/reorder-matches` — body: `{ordered_match_ids: []}`
- `POST /matches/{id}/reassign-judge` — body: `{new_judge_id}`. For stuck matches.

**Broadcast**
- `POST /tournaments/{id}/broadcasts` — body: `{message, target_subscribers, target_public_dashboard}`

**Backups**
- `GET /tournaments/{id}/backups` — list available snapshots (auto + automatic-pre-action)

**Operational**
- `GET /tournaments/{id}/unclaimed-summary` — returns count of unclaimed round-robin matches across divisions; powers admin home banner
- `GET /admin/preview-token?role=judge` — issues a read-only judge JWT for preview-as mode (cannot claim/score)

**Activity log**
- `GET /tournaments/{id}/activity?since={timestamp}&division_id={id}`

### Judge (require judge JWT)
- `GET /divisions` — active list with match counts
- `GET /divisions/{id}/matches`
- `POST /matches/{id}/claim` — assigns this judge; rejects if judge already has an active match elsewhere or if match already claimed
- `POST /matches/{id}/release` — un-assign before starting (still `scheduled`)
- `POST /divisions/{id}/reorder-matches`
- `POST /matches/{id}/start`
- `POST /matches/{id}/rounds/{round_number}/start`
- `POST /matches/{id}/rounds/{round_number}/pause`
- `POST /matches/{id}/rounds/{round_number}/resume`
- `POST /matches/{id}/rounds/{round_number}/end`
- `POST /matches/{id}/score` — body: `{competitor_id, delta, client_event_id}` — current round only; idempotent
- `POST /matches/{id}/score/undo` — undoes most recent un-undone score event
- `POST /matches/{id}/forfeit` — body: `{competitor_id}` → moves match to `pending_review`
- `POST /matches/{id}/submit` — final commit; only allowed when final round has ended

### Public (no auth, `X-Device-Id` header)
- `GET /tournaments/active/dashboard` — slideshow data
- `GET /divisions/{id}/public` — current standings, current match (public-safe), next match
- `GET /participants/{id}/public` — competitor record
- `POST /subscriptions` — body: `{participant_id?, tournament_wide?, web_push_endpoint?}`
- `DELETE /subscriptions/{id}`
- `GET /subscriptions?device_id=...`

### SSE streams
- `GET /sse/divisions/{id}` — live score updates, match state changes, standings recalcs (judge/admin only)
- `GET /sse/dashboard` — slideshow tick + division updates (judge/admin only)
- `GET /sse/activity?tournament_id={id}` — activity log feed (admin only)

> **Public surfaces don't use SSE** — they poll. See [`architecture.md`](architecture.md#realtime-strategy).

## Judge code generation

- 8 characters: 7 random + 1 checksum.
- Charset: `23456789ABCDEFGHJKLMNPQRSTUVWXYZ` (32 chars; excludes `0/O`, `1/I/L`).
- Checksum: Luhn-mod-32 over the first 7.
- Tournament-scoped uniqueness, not global.
- On collision during generation, regenerate (chance is negligible but handle it).
- On invalid checksum at login: reject with "invalid code" (don't leak whether the prefix exists).

## Background jobs

- **Auto-release stale matches**: scan every 60s for `state = 'paused'` matches where `last_action_at` is older than `judge_auto_release_seconds`. Release the judge assignment, set `state = 'scheduled'`, write `system` activity log entry. **Never auto-release `in_progress` matches.**
- **Web Push fan-out**: triggered by SSE pub/sub events on subscribed channels. Sends VAPID push to subscriptions where `web_push_endpoint IS NOT NULL`.

## Concurrency safety

- Match claim: `UPDATE matches SET assigned_judge_id = :judge WHERE id = :match AND assigned_judge_id IS NULL` — driven by row-level locking. If 0 rows updated, return 409.
- Score events: server validates `match.state = 'in_progress'` and `round.state = 'running'` before accepting.
- Round timer: server-authoritative, see [`correctness.md`](correctness.md#timer-authority).
- Parallel matches in round-robin: competitor-conflict check before allowing match start. See [`correctness.md`](correctness.md#parallel-matches-within-a-division).
- Single-match enforcement during play-ins/semis/finals/bronze. See [`correctness.md`](correctness.md#parallel-matches-within-a-division).
- Division-paused enforcement: judges cannot claim or start matches in a paused division. Already-running rounds continue ticking. See [`correctness.md`](correctness.md#division-pause-blocks-judge-actions).

## Rate limiting

Per-IP rate limiting via `slowapi`. Full table in [`operations.md`](../infra/operations.md#rate-limiting).

Key limits to remember:
- Public endpoints: 60 req/min
- Login endpoints (admin/judge): 5 attempts per 15 min
- SSE connections: 5 per IP
- All other authenticated endpoints: 600 req/min

CloudFront caches `GET /tournaments/active/dashboard` for 3 seconds at the edge as defense-in-depth.

## Standings cache

Standings computation is non-trivial (filter matches → group by competitor → sort by tie-break rules). Caching prevents N²-ish work on every public poll.

- Computed once per submitted match.
- Cached in Redis with key `standings:division:{id}`, TTL 1 hour.
- Invalidated on:
  - Match submission
  - Match result edit
  - Late participant addition
  - Bracket advancement
- Public read: cache-hit returns precomputed list.

## Post-tournament behavior

After `lifecycle_state = 'completed'`:
- Public URLs continue to work indefinitely (until admin deletes the tournament).
- All write endpoints return 409 `TOURNAMENT_COMPLETED` for non-admin actors.
- Admin retains read access; admin write endpoints return 409 except for `DELETE /tournaments/{id}` (soft delete).
- Subscribers receive a final tournament-wide notification: "Tournament complete — congratulations to medal winners."
- Hourly backup job stops automatically.
- Activity log retained but read-only.
