# Memory: Decisions & Gotchas

Append-only log of decisions made, gotchas discovered, and things that are easy to forget. Newest entries at the top.

## Decisions

### 2026-04 — Round 3 of refinements

- **BDD adoption**: Hybrid. Gherkin (`pytest-bdd`) for tournament rules / scoring / brackets / standings. Plain pytest for everything else.
- **Broadcast targets**: Two independent booleans (`target_subscribers`, `target_public_dashboard`). Dropped the `all` enum.
- **Backups**: All automatic. No "Snapshot Now" button. Pre-action snapshots are server-triggered before risky operations. No restore-from-UI; restore is a manual ops procedure.
- **Demo mode**: Drop the reset endpoint. Admin deletes + recreates demo tournaments instead. One less code path.
- **Hint card**: Replaced with single-line helper text above match queue. No localStorage state.
- **Color zones**: Per-match positional (a = red, b = blue), reinforced with text labels and screen position.
- **Result display**: Standard / sudden-death / forfeit each have explicit format strings. No raw numeric round counts when sudden-death applies.
- **Pending review state**: Public dashboard shows "Match concluded — awaiting submission" instead of live scores during the brief judge review window.
- **Server clock**: All server-side timestamps use Postgres `now() AT TIME ZONE 'utc'`, never Python `datetime.utcnow()`. Single clock prevents drift.
- **Score events vs results**: Score events are immutable audit trail. Admin result edits update `match_rounds` but preserve `score_events`. Documented as intentional divergence.
- **Division pause**: Blocks judge claim/start; doesn't disrupt running rounds. Already-running rounds tick to completion.
- **Re-subscription**: Un-soft-deletes the existing row. Upsert by `(device_id, participant_id)` unique key.
- **Notification dedup**: One toast/push per `(device_id, broadcast_id)`, regardless of how many participant subscriptions.
- **Non-top-4 ties**: Displayed as ties in standings; never trigger play-ins.
- **Forfeit during sudden-death**: Allowed; same behavior as regular forfeit.
- **Activity log granularity**: Score events do NOT log; only state transitions do.
- **Print views**: Two routes — `/divisions/:id/print` and `/matches/:id/print`.
- **Admin "Preview as"**: Read-only judge token + new tab for public preview.
- **Unclaimed match alert**: Yellow banner on admin home if 3+ matches unclaimed for 15+ min.

### 2026-04 — Round 2 of refinements

- **Deployment**: Switched back to App Runner + self-hosted Redis on EC2 t4g.nano. Cost-driven; hardened with `restart: always`, systemd, EC2 auto-recovery, and CloudWatch alarms. Migration to ElastiCache is one-day work if needed later.
- **Parallel matches**: During round-robin only, multiple matches per division allowed if no competitor overlap. Final 4 phase is strictly sequential.
- **Late additions**: Admin can add participants during round-robin; new matches are *appended*, never invalidating played ones. Blocked after bracket starts.
- **Backups**: Three-layer — Supabase nightly + hourly during active tournaments + automatic pre-action snapshots. (Updated round 3: dropped manual button.)
- **Admin UI**: Desktop-only. < 1024px viewport shows "use desktop" message.
- **Time zone**: IANA TZ captured from admin browser at tournament creation. Stored on `tournaments.time_zone`.
- **Competitor finder**: Skipped (KISS).
- **Queue position**: Shown as "#N in queue" on public; no time estimates.
- **Broadcasts**: Admin chooses target. (Updated round 3: two booleans, not enum.)
- **Post-tournament view**: Stays accessible read-only forever (until admin deletes).
- **Monitoring**: KISS — CloudWatch logs only. No Sentry, no UptimeRobot.
- **Rate limiting**: Per-IP via `slowapi`. Public 60/min, login 5/15min, SSE 5/IP. CloudFront 3s edge cache as defense-in-depth.
- **Judge offline**: Show "OFFLINE — cannot score" overlay; no queueing.
- **Judge multi-device**: JWT bound to single device via `jti`. New login invalidates old.

### 2026-04 — Final spec lock-in

- **Scoring**: simple `+1` / `-1` buttons, generic. No technique-based scoring.
- **One judge per match.** Misclick recovery via undo (not multi-judge averaging).
- **Architecture**: `React → FastAPI → SQLAlchemy → Supabase Postgres`. Frontend never talks to Supabase directly.
- **Realtime**: SSE for judge/admin, polling for public dashboard. Redis pub/sub for SSE fan-out across uvicorn workers.
- **Frontend state**: switched from Redux to Zustand + TanStack Query.
- **Match end condition**: highest cumulative score across all rounds.
- **Bracket structure**: round-robin → play-ins (only if needed) → semis (1v4, 2v3) → finals + bronze.
- **One participant, one division.**
- **Divisions run in parallel.**
- **Public users**: anonymous, device UUID in localStorage. No email/account.
- **Notifications**: in-app toasts + web push.
- **Admin auth**: Supabase email/password.
- **Judge codes**: 8 chars + checksum (Luhn-mod-32), tournament-scoped.

## Gotchas

### Round-robin with odd N
True round-robin where every competitor faces every other competitor exactly once **requires one competitor to rest each round** when N is odd. Unavoidable mathematically. We don't record a "bye match" — the resting competitor simply doesn't play that round. Surface who's resting in the UI.

### Parallel matches in round-robin only
Multiple matches can run simultaneously **only during round-robin**. Play-ins, semis, finals, and bronze are strictly one-at-a-time per division. Don't forget the phase check at start time.

### Competitor-conflict at match start
Before allowing a match to start, check no competitor is in another in-progress/paused match in the same division. Easy to miss. Returns 409 with conflicting match id.

### Late additions append, don't regenerate
When admin adds a participant during round-robin, generate matches against existing competitors and **append** to queue. Never invalidate already-played matches. Standings recompute naturally.

### Server-authoritative timer
The server is the source of truth for round time. Client only displays. Schema fields: `started_at`, `accumulated_paused_seconds`, `ended_at`. Computing elapsed time uses `(now - started_at) - accumulated_paused_seconds`. Never extrapolate forward from a paused state on the client.

### Score idempotency
`POST /matches/{id}/score` requires a `client_event_id` (UUID). Server dedupes via unique index on `(match_id, client_event_id)`. Network retries can't double-count.

### Score undo via append-only log
Don't store running scores as a column. Always derive from `score_events` filtered by `undone_at IS NULL`. Undo just sets `undone_at = now()` on the latest event in the current round.

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
On any reconnect (page load OR SSE drop), judges must re-fetch full match state from server. Local cache is untrusted. Use full snapshot, not deltas.

### Public dashboard does not use SSE
It polls every 3–5s. SSE concurrency cost too high for the largest audience. Judges and admin (small audiences) get SSE.

### CloudFront caches the dashboard endpoint
3-second edge cache on `GET /tournaments/active/dashboard`. Cuts origin load from N×polls to 1 every 3s. Cache key includes `X-Device-Id`.

### Web push delivery is best-effort
On 410 Gone from a push provider, soft-delete the `web_push_endpoint` but keep the in-app subscription. Never block API responses on push delivery — fire and forget.

### Soft delete everywhere
All tables use `deleted_at`. List queries filter `WHERE deleted_at IS NULL`. Saves us from data-loss disasters.

### Demo mode is reset-able
`is_demo = true` tournaments are excluded from public view and have a reset endpoint. Used for staff training and pre-event rehearsal. Don't accidentally promote a demo tournament to active without resetting it.

### Print view is a real feature
`/divisions/:id/print` with `@media print` styles. Tournament organizers want a paper backup. Cheap insurance against network failures at the venue.

### Submit button is disabled until final round ends
Don't let judges submit early. The button enables only when the last round's `state = 'completed'` (or on forfeit).

### Sudden-death has no time limit
No timer. Next point wins. Make sure UI removes the timer entirely (not just sets it to a high number).

### Activity log includes `actor_display_name`
Denormalize the actor's name at write time. Don't join through soft-deleted judges/admins on read.

### Activity log doesn't track score events
Score events live in `score_events` table. Activity log records state transitions only (claim, start, pause, end_round, forfeit, submit, edit_result, etc.). Don't accidentally log every `+1` — the feed becomes unscannable.

### Score events are immutable
When admin edits a submitted result, `match_rounds` and `matches.winner_id` change but `score_events` are preserved as audit trail. Post-edit, events may not sum to recorded round scores. That's intentional.

### Postgres `now()` is the only clock
Always use `func.now()` in SQLAlchemy or `now() AT TIME ZONE 'utc'` in raw SQL. Never `datetime.utcnow()` from Python. Prevents drift between FastAPI workers and DB.

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
No restore-from-UI. Manual procedure documented in operations runbook. Restoring in front of users mid-tournament is high-risk; deliberate engineer action only.

### Demo deletion, not reset
Demo tournaments are deleted + recreated to reset. No reset endpoint. Less code path complexity.

### Forfeit during sudden-death is allowed
Same behavior as regular forfeit. Match ends, opponent wins. Don't add special-case handling.

### Non-top-4 ties don't trigger play-ins
Standings show ties as ties. Play-ins are only for ties affecting bracket entry.

### Result display format
Use the explicit format strings: "X def. Y A-B in N rounds" / "X def. Y A-B in sudden-death" / "X def. Y (forfeit)". Never display a numeric round count for sudden-death matches.

### Backups stop when tournament completes
The hourly backup job is gated on `tournaments.lifecycle_state = 'active'`. When tournament completes, job stops automatically. Don't accumulate snapshots forever.

### Standings cache invalidation
Cached in Redis; invalidate on match submit, result edit, late addition, bracket advancement. Easy to forget on the late-addition path.

### Admin removing an active judge
Forces logout (clears `current_session_jti`), pulls them off any active match (state → `paused`, requires admin reassignment). Confirmation modal must surface this consequence.

## Things to double-check before tournament day

See [`operations.md`](../infra/operations.md#pre-tournament-checklist) for the full checklist.

## Naming conventions

- Database tables: `snake_case`, plural.
- API routes: `kebab-case` for path segments, `snake_case` for body keys.
- TypeScript types: `PascalCase`.
- Zustand stores: `useFooStore`.
- TanStack Query keys: tuples `['resource', id]` or `['resource', { filter }]`.
- Activity log `action`: `dot.notation`, e.g., `match.submitted`, `division.paused`, `participant.added_late`.
