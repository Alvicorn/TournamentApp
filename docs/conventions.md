# Conventions & Gotchas

Quick-reference cheat sheet. The full rules live in [`correctness.md`](correctness.md), [`backend.md`](backend.md), and [`product.md`](product.md) — this page is the compressed version to keep in mind while coding.

## Naming conventions

- Database tables: `snake_case`, plural.
- API routes: `kebab-case` for path segments, `snake_case` for body keys.
- TypeScript types: `PascalCase`.
- Zustand stores: `useFooStore`.
- TanStack Query keys: tuples `['resource', id]` or `['resource', { filter }]`.
- Activity log `action`: `dot.notation`, e.g., `match.submitted`, `division.paused`, `participant.added_late`.

## Gotchas

### Round-robin with odd N
True round-robin where every competitor faces every other competitor exactly once **requires one competitor to rest each round** when N is odd. We don't record a "bye match" — the resting competitor simply doesn't play that round. Surface who's resting in the UI.

### Parallel matches in round-robin only
Multiple matches can run simultaneously **only during round-robin**. Play-ins, semis, finals, and bronze are strictly one-at-a-time per division. Don't forget the phase check at start time.

### Competitor-conflict at match start
Before allowing a match to start, check no competitor is in another in-progress/paused match in the same division. Easy to miss. Returns 409 with conflicting match id.

### Late additions append, don't regenerate
When admin adds a participant during round-robin, generate matches against existing competitors and **append** to queue. Never invalidate already-played matches. Standings recompute naturally.

### Server-authoritative timer
The server is the source of truth for round time. Client only displays. Schema fields: `started_at`, `accumulated_paused_seconds`, `ended_at`. Computing elapsed time uses `(now - started_at) - accumulated_paused_seconds`. Never extrapolate forward from a paused state on the client. Offline exception: replayed outbox commands use client timestamps (deltas from one clock), sanity-bounded by the server.

### Score idempotency
`POST /matches/{id}/score` requires a `client_event_id` (UUID) and `client_recorded_at` (tap time). Server dedupes via unique index on `(match_id, client_event_id)`. Network retries and offline outbox replays can't double-count.

### Score undo via append-only log
Don't store running scores as a column. Always derive from `score_events` filtered by `undone_at IS NULL`. Undo just sets `undone_at = now()` on the latest event in the current round.

### Offline outbox is never silently discarded
If an outbox flush is rejected (match reassigned, judge removed), the events are shown to the judge for manual recovery with the admin. Silently dropping recorded scores is the worst failure mode this feature can have.

### Auto-release ONLY paused matches
Auto-release scans for `state = 'paused'` with stale `last_action_at`. **Never auto-release `in_progress`** — silently grabbing a half-scored running match is worse than the original problem. For in-progress stuck matches, admin must manually reassign.

### Editing submitted matches has tiered consequences
- During round-robin: just recalc standings.
- After round-robin advanced: admin must explicitly choose record-only vs full bracket regeneration. Default is record-only.

### Custom fields freeze on tournament activation
`custom_participant_fields` mutable in `setup`, immutable in `active`. Reverting to `setup` makes it mutable again, but UI must warn that existing participant data may have null values for new fields.

### Judge codes are tournament-scoped
Login requires both `tournament_id` and `code`. Don't fall back to a global lookup.

### Judge sessions are single-device
JWT carries `jti` claim; `judges.current_session_jti` is the only valid one. New login invalidates previous device. **Active match is NOT auto-released** on new login (assumed same person switching devices).

### Reconnect behavior
On any reconnect (page load OR SSE drop), judges **flush the offline outbox first**, then re-fetch full match state from server. Local cache is untrusted *except the outbox* (it's the record of what the server hasn't seen). Use full snapshot, not deltas.

### Public dashboard does not use SSE
It polls every 3–5s. SSE concurrency cost too high for the largest audience. Judges and admin (small audiences) get SSE.

### Dashboard endpoint is cached in-process
3-second in-process cache on `GET /tournaments/active/dashboard`. Cuts DB load from N×polls to 1 computation every 3s. The response must stay **device-neutral** — per-device data (e.g., my subscriptions) lives on separate endpoints, or the cache is defeated.

### Single worker is a hard constraint
In-process pub/sub and caches assume one instance, one uvicorn worker. Bumping `--workers` or adding instances silently breaks SSE fan-out and cache invalidation. If scale demands it, add a broker (Postgres `LISTEN/NOTIFY` or Redis) first.

### Render free tier spins down; Supabase free tier pauses
UptimeRobot's 5-min `/health` pings keep Render awake (750 free hrs/mo covers 24/7). Supabase pauses idle projects after ~1 week — check the dashboard days before an event, not morning-of.

### Web push delivery is best-effort
On 410 Gone from a push provider, soft-delete the `web_push_endpoint` but keep the in-app subscription. Never block API responses on push delivery — fire and forget.

### Soft delete everywhere
All tables use `deleted_at`. List queries filter `WHERE deleted_at IS NULL`. Saves us from data-loss disasters.

### Demo mode "reset" = delete + recreate
`is_demo = true` tournaments are excluded from public view. There is **no reset endpoint** — admins delete and recreate the demo. Don't accidentally promote a stale demo tournament to active.

### Print view is a real feature
`/divisions/:id/print` with `@media print` styles. Tournament organizers want a paper backup. Cheap insurance against network failures at the venue.

### Submit button is disabled until final round ends
Don't let judges submit early. The button enables only when the last round's `state = 'completed'` (or on forfeit) AND the offline outbox is drained.

### Sudden-death has no time limit
No timer. Next point wins. Make sure UI removes the timer entirely (not just sets it to a high number).

### Activity log includes `actor_display_name`
Denormalize the actor's name at write time. Don't join through soft-deleted judges/admins on read.

### Activity log doesn't track score events
Score events live in `score_events` table. Activity log records state transitions only (claim, start, pause, end_round, forfeit, submit, edit_result, etc.). Don't accidentally log every `+1` — the feed becomes unscannable.

### Score events are immutable
When admin edits a submitted result, `match_rounds` and `matches.winner_id` change but `score_events` are preserved as audit trail. Post-edit, events may not sum to recorded round scores. That's intentional.

### Postgres `now()` is the only clock
Always use `func.now()` in SQLAlchemy or `now() AT TIME ZONE 'utc'` in raw SQL. Never `datetime.utcnow()` from Python. Prevents drift between the FastAPI worker and DB. (Offline-replayed commands are the one exception — see the timer gotcha above.)

### Pending review state needs distinct public UX
Between match end and submission, public dashboard should show "Match concluded — awaiting submission" instead of live scores. Don't leave the live score frozen mid-screen.

### Division-paused enforcement
Judges cannot claim or start matches in paused divisions. Already-running rounds continue ticking. Don't disrupt mid-round.

### Re-subscribe upserts
When a public user re-subscribes, un-soft-delete the existing row by `(device_id, participant_id)`. Don't accumulate dead subscription rows.

### Notification dedup is per-broadcast, per-device
Subscriber following 5 competitors gets ONE toast per broadcast, not five. Dedup by `(device_id, broadcast_id)` server-side.

### Pre-action snapshots are automatic
Before bracket regeneration, result edit, lifecycle transitions, late additions — server takes a snapshot first. No admin button. Admin sees the result in `/admin/backups`.

### Restore is engineer-only
No restore-from-UI. Restoring in front of users mid-tournament is high-risk; deliberate engineer action only (via Supabase SQL editor from R2 dumps).

### Non-top-4 ties don't trigger play-ins
Standings show ties as ties. Play-ins are only for ties affecting bracket entry.

### Forfeit during sudden-death is allowed
Same behavior as regular forfeit. Match ends, opponent wins. Don't add special-case handling.

### Result display format
Use the explicit format strings: "X def. Y A-B in N rounds" / "X def. Y A-B in sudden-death" / "X def. Y (forfeit)". Never display a numeric round count for sudden-death matches.

### Backups stop when tournament completes
The hourly backup job is gated on `tournaments.lifecycle_state = 'active'`. When tournament completes, job stops automatically. Don't accumulate snapshots forever.

### Standings cache invalidation
Cached in-process; invalidate on match submit, result edit, late addition, bracket advancement. Easy to forget on the late-addition path.

### Admin removing an active judge
Forces logout (clears `current_session_jti`), pulls them off any active match (state → `paused`, requires admin reassignment). Confirmation modal must surface this consequence — including that the judge may be **scoring offline**, in which case their unsynced events will be rejected on sync.
