# Correctness Guarantees

This document captures the correctness-critical behaviors that are easy to get wrong and where bugs would cause real-world damage (invalid results, frozen scoreboards, misattributed wins).

## Timer authority

**The server is the authoritative source of round time.** The client only displays time; it never decides time.

### Single clock: Postgres `now()`
All server-side timestamps come from Postgres `now() AT TIME ZONE 'utc'`, **not** Python's `datetime.utcnow()`. This avoids drift between the FastAPI process clock and the database. SQLAlchemy `server_default=func.now()` handles inserts; explicit `now()` in UPDATE statements handles modifications.

Why this matters: under load, a Python clock can be 50–200ms behind the DB. For a sudden-death scenario where two scores arrive milliseconds apart, this matters.

### Schema
- `match_rounds.started_at` — set when the round transitions to `running`.
- `match_rounds.accumulated_paused_seconds` — incremented by `(now - paused_at)` each time a paused round resumes.
- `match_rounds.ended_at` — set when the round completes.

### Client display
```
elapsed = (now - started_at) - accumulated_paused_seconds
remaining = round_length_seconds - elapsed
```

When the round is `paused`, the client freezes display at the last known elapsed value — it does not extrapolate forward.

### Server pause/resume
Each pause increments `accumulated_paused_seconds` atomically:
```
UPDATE match_rounds
SET accumulated_paused_seconds = accumulated_paused_seconds + EXTRACT(EPOCH FROM (now() - paused_at)),
    state = 'paused',
    paused_at = now()
WHERE id = :round_id AND state = 'running';
```

### SSE events for time
- `round.started`: `{started_at, round_length_seconds}`
- `round.paused`: `{paused_at, accumulated_paused_seconds}`
- `round.resumed`: `{resumed_at, accumulated_paused_seconds}`
- `round.ended`: `{ended_at}`

The client recomputes display from these timestamps; client clock skew is irrelevant because we only use deltas relative to `started_at`.

### Offline exception
For round-control commands replayed from an offline outbox, the **client's recorded timestamps become the authoritative event times** (`match_commands.occurred_at`). Pause/resume durations are computed from *deltas between client timestamps*, which are immune to absolute clock skew because they come from one device clock. The server sanity-bounds replayed timestamps: not in the future (vs. server `now()` + small tolerance), not before the round's `started_at`, and strictly monotonic within the replayed sequence. Out-of-bound commands are rejected with 422 and surfaced to the judge. See [Judge offline scoring](#judge-offline-scoring).

## Score idempotency

Network retries must not double-count. Misclicks must be undoable.

### Idempotency
Each score event from the client carries a `client_event_id` (UUID) and a `client_recorded_at` timestamp (when the judge actually tapped). Server dedupes on `(match_id, client_event_id)` via unique index. A retry with the same id returns the same response without applying the delta a second time. This same mechanism makes offline outbox replay safe — a flush interrupted halfway can simply start over from the top.

### Undo
- All score events are stored in `score_events` (append-only).
- The judge's UI shows the last 3 un-undone events with undo buttons.
- `POST /matches/{id}/score/undo` marks the most recent un-undone event for the **current round** as undone (`undone_at = now()`) and returns the updated score.
- Undone events are still visible in the admin audit view.

### Computing current score
Always derive from the score_events table; never store running totals as a column:
```sql
SELECT competitor_id, SUM(delta) AS score
FROM score_events
WHERE match_id = :id AND round_number = :n AND undone_at IS NULL
GROUP BY competitor_id;
```

## Reconnect behavior (judges)

Judges can lose network mid-match (Wi-Fi flaps, phone sleeps, etc.). While offline they keep scoring into the local outbox (see [Judge offline scoring](#judge-offline-scoring)); reconnect is when local and server state converge.

### On reconnect (page load or SSE reconnect)
1. **Flush the outbox first**: replay queued score events and round commands to the server, in recorded order, through the normal endpoints (idempotent). The outbox must drain before any state fetch, otherwise the fetch would "roll back" the judge's local view.
2. Fetch full match state including all rounds and current scores (full snapshot, not delta).
3. Replace local Zustand state with the server snapshot. After a successful flush this matches what the judge was already seeing.
4. Reconnect SSE and resume listening.
5. If the flush was rejected (match reassigned/judge removed → 409), do NOT discard the outbox silently — see the conflict handling in [Judge offline scoring](#judge-offline-scoring). Show the toast and route to the division match queue.

**Never trust local state after a connection gap** — except the outbox, which is precisely the record of what the server hasn't seen yet. Everything else is replaced by the server snapshot.

## Stuck match recovery

Two mechanisms:

### 1. Auto-release (system)
Background job releases `paused` matches with stale `last_action_at`:
- Default: 10 minutes of inactivity.
- Configurable via `tournaments.judge_auto_release_seconds`.
- Releases ONLY paused matches. Never releases `in_progress` (that would be worse — a half-scored running match getting silently grabbed by another judge).
- Writes a `system` actor entry to `activity_log`.

### 2. Admin reassignment (manual)
Admin can call `POST /matches/{id}/reassign-judge` for any match in any state. This:
- Removes the current judge assignment.
- Sets `assigned_judge_id` to the new judge.
- If the match was `in_progress`, sets `state = 'paused'`.
- Writes to `activity_log` with admin actor.
- Notifies both judges via SSE.

## Editing submitted matches

Admin-only. Tiered consequences depending on division phase.

### Phase 1: Round-robin still active
- Edit the match result.
- Recalculate standings.
- Notify subscribers of affected competitors with "result corrected" push.
- No bracket impact yet.

### Phase 2: Division has advanced past round-robin
This is the dangerous case. The bracket may now be wrong.

API: `POST /matches/{id}/edit-result` with body `{round_scores: [...], regenerate_bracket: bool}`.

Two modes the admin must explicitly choose:
- **Record-only (`regenerate_bracket: false`, default)**: Update the match in the database for record-keeping. Standings are recomputed but the bracket is not regenerated. Existing play-in/semi/final/bronze matches remain. Useful when the correction is cosmetic or the bracket already played through.
- **Full regeneration (`regenerate_bracket: true`)**: Hard warning in admin UI. Destroys all play-in/semi/final/bronze matches (soft delete with `deleted_at` for audit) and re-runs `advance-bracket`. Use only when the wrong competitors advanced.

Both modes write to `activity_log`.

## Custom field freezing

When tournament transitions from `setup` to `active`:
- `custom_participant_fields` becomes immutable.
- Attempting to edit returns 409 Conflict with a clear error.
- If admin forces back to `setup`, the field spec becomes mutable again, but UI warns about existing participant data.

While in `setup`:
- Adding a new field: existing participants get `null` for the new field's value; UI flags participants with missing required fields.
- Removing a field: existing participants' values for that field are dropped from `custom_fields` JSON.
- Changing a field's `key`: equivalent to remove + add (existing values lost). UI warns explicitly.

## Web push delivery

Web push is best-effort, not guaranteed delivery.

- Subscriptions can fail (browser permission revoked, endpoint expired).
- On a 410 Gone response from a push provider, soft-delete the subscription's `web_push_endpoint` (set to null) but keep the in-app subscription.
- In-app toasts are always delivered when the tab is open. Web push only matters when the tab is closed.
- Don't block API responses on push delivery — fire and forget via background task.

## Race condition — two judges claim same match

Handled at the database layer:
```sql
UPDATE matches
SET assigned_judge_id = :judge_id
WHERE id = :match_id
  AND assigned_judge_id IS NULL
  AND deleted_at IS NULL
RETURNING *;
```

If `0` rows updated → return 409 Conflict to the second judge with the current assignee's name in the error.

## Race condition — judge with active match claims another

Service-layer check before the UPDATE:
```sql
SELECT 1 FROM matches
WHERE assigned_judge_id = :judge_id
  AND state IN ('in_progress', 'paused', 'pending_review')
  AND deleted_at IS NULL;
```

If row exists → return 409 with the existing match id.

## Parallel matches within a division

During **round-robin only**, multiple matches can run simultaneously within a division as long as no competitor is in two matches at once. During **play-ins, semis, finals, and bronze**, only one match at a time per division.

### Conflict check on match start
Before transitioning a match from `scheduled` to `in_progress`:
```sql
SELECT 1 FROM matches
WHERE division_id = :div_id
  AND state IN ('in_progress', 'paused')
  AND deleted_at IS NULL
  AND (
    competitor_a_id IN (:a_id, :b_id)
    OR competitor_b_id IN (:a_id, :b_id)
  );
```
If row exists → return 409 with the conflicting match id and competitor name.

### Phase enforcement
Beyond round-robin, also enforce single-match limit:
```sql
-- For non-round-robin phases
SELECT 1 FROM matches
WHERE division_id = :div_id
  AND state IN ('in_progress', 'paused')
  AND phase != 'round_robin'
  AND deleted_at IS NULL;
```
If `1+` rows exist when starting a play-in/semi/final/bronze → return 409.

### Judge UI implications
- Match queue shows competitor-conflict matches as **grayed out and unclaimable** with tooltip: "Alice is in Match #4."
- Once the conflicting match completes, the queued match becomes claimable (state-driven, no manual refresh).

### Public dashboard implications
- Up to **2 simultaneous matches** per division shown as split view.
- 3+ simultaneous → cycle through them as separate slideshow slides for that division.
- "Current match" in API responses returns an array, not a single object.

## Late participant additions

Admin can add participants to a division **after** the tournament is `active`, including after round-robin has started. Strict rules:

### Allowed
- Adding a participant during `round_robin` phase: the new participant gets matches generated against every existing competitor in the division. These matches are **appended** to the queue (highest `order_index`), not interleaved.
- Adding a participant before any matches have started in a division: equivalent to a normal addition.

### Disallowed
- Adding a participant after the division has advanced to `play_ins`, `semis`, `finals`, or `completed`. Hard-rejected with a clear error.

### Implementation
```python
def add_late_participant(division, participant):
    if division.state != "round_robin":
        raise HTTPException(409, "Division has advanced past round-robin; late additions not allowed")

    existing = get_active_participants(division)
    new_matches = []
    for opponent in existing:
        new_matches.append(Match(
            division_id=division.id,
            competitor_a_id=participant.id,
            competitor_b_id=opponent.id,
            phase="round_robin",
            order_index=next_order_index(division),
            state="scheduled",
        ))
    save_all(new_matches)
    log_activity("participant.added_late", actor=admin, metadata={"new_matches": len(new_matches)})
```

### Activity log
- Every late addition writes a prominent `participant.added_late` entry visible in admin activity feed.
- Subscribers get no special notification (their subscription is per-participant).

## Judge multi-device sessions

Judge sessions are **bound to a single device**. New login from a different device invalidates the previous session.

### JWT structure
- Each judge JWT carries a `jti` (JWT ID) claim — a fresh UUID per login.
- Judge's current valid `jti` is stored in `judges.current_session_jti` (single-value column).
- Every authenticated judge request validates: token's `jti` matches `judges.current_session_jti`.

### Login flow
```python
def judge_login(tournament_id, code):
    judge = find_judge_by_code(tournament_id, code)
    new_jti = uuid4()
    judge.current_session_jti = new_jti  # Overwrites previous
    db.commit()

    token = sign_jwt({
        "sub": judge.id,
        "jti": str(new_jti),
        "exp": now() + 24h,
        "tournament_id": tournament_id,
    })
    return token
```

### When a previous device's token is rejected
- API returns 401 with code `SESSION_INVALIDATED`.
- Client shows toast: "Logged in from another device. Please log in again to continue."
- Redirects to judge login.

### Edge case: judge mid-match logs in elsewhere
- Active match is **not auto-released**. The judge is presumed to be the same person, just switching devices.
- New device sees the in-progress match as their active match on first load.
- Old device gets `SESSION_INVALIDATED` on next API call.

## Judge offline scoring

Judge scoring **keeps working offline**. The judge's device is the only writer to its match (single judge per match + single-device sessions), so a local-first queue is safe: actions are recorded locally with the device's timestamp, applied optimistically to the UI, and replayed to the server when connectivity returns.

> This reverses an earlier decision to disable scoring offline. The original objection — "score timing matters, queueing mis-records it" — is resolved by capturing `client_recorded_at` at tap time: a replayed event carries the exact moment the judge tapped, not the moment the network recovered.

### What works offline
- Scoring: `+1` / `-1` / undo.
- Round control: pause, resume, end round.
- Sudden-death entry: if the final round ends tied while offline, the client enters sudden-death locally — the trigger is a deterministic rule, so client and server reach the same conclusion when the queue replays.
- A page refresh: the PWA service worker serves the app shell, and the outbox + match snapshot are persisted locally.

### What requires network
- **Submit** (the final, irreversible commit) — and it additionally requires the outbox to be fully drained, so a submitted match always reflects every recorded event.
- Claiming or starting a *new* match (server must arbitrate contention).

### Detection
- Browser's `navigator.onLine` + fetch failures (1 failed request → treat as offline).
- While offline: show the non-blocking offline banner ([`frontend.md`](frontend.md#judge-offline-banner)); keep all scoring/round buttons enabled.

### The outbox
- Persistent client-side queue (IndexedDB; localStorage fallback), keyed by match id, surviving refresh and tab close.
- Each entry is exactly the payload of a normal API call: score events `{competitor_id, delta, client_event_id, client_recorded_at}` and round commands `{command, round_number, client_command_id, occurred_at}`.
- When online, the outbox is write-through: entries are appended and flushed immediately (normal operation is just an outbox with zero latency). When offline, entries accumulate.
- Flush is strictly in recorded order, one at a time, through the normal endpoints. Idempotency keys make an interrupted flush restartable from the top.

### Timer math on replay
Pause/resume durations are computed from deltas between the replayed commands' client timestamps — one device clock, so absolute skew cancels out. Server sanity bounds: not in the future, not before round start, monotonic within the sequence. See [Timer authority — offline exception](#offline-exception).

### Conflict handling
The only writer conflict is an admin acting while the judge is offline:

- **Admin reassigns the match or removes the judge** → the flush hits 401/409. The client must NOT discard the outbox: show "This match was reassigned — your N offline events were NOT recorded" with the events viewable (competitor, delta, time) so the score can be reconstructed manually with the admin. The admin reassignment UI warns: "The assigned judge may be scoring offline; their unsynced events will be rejected."
- **Auto-release**: `in_progress` matches are never auto-released, so a judge offline mid-round keeps their assignment indefinitely. A match left `paused` past the auto-release threshold *can* be released while the judge is offline; if another judge claims it, the original judge's flush resolves through the same 409 path above.
- Anything else (SSE events missed while offline, standings changes) is read-only state, restored by the post-flush snapshot fetch.

### Recovery
- On reconnect: flush outbox → re-fetch full match state → replace local state (per [reconnect behavior](#reconnect-behavior-judges)).
- Toast: "Back online — N events synced."

## Judge kicked / removed by admin

When admin removes a judge (via `DELETE /judges/{id}`):

1. `judges.is_active = false`, `judges.deleted_at = now()`, `judges.current_session_jti = null`.
2. If the judge has an active match (`assigned_judge_id = :id` AND `state IN ('in_progress', 'paused', 'pending_review')`):
   - Match transitions to `paused` (if not already).
   - `assigned_judge_id` set to `null`.
   - Activity log entry: `match.judge_removed_by_admin`.
   - Admin sees a banner reminding them to reassign the match.
3. The kicked judge's next API call returns 401 `SESSION_INVALIDATED`.
4. Client redirects to judge login; login fails with "Code not recognized" (we don't leak that the judge existed).

### Admin UI cue
- Removing an active judge shows a confirmation modal: "Maria has an active match (Match #12). Removing her will pause that match. Continue?"
- After removal, the affected match is highlighted in the admin view with a "Needs reassignment" badge.

## Forfeit during sudden-death

Forfeit is allowed at any time during a match, including sudden-death. The behavior is identical to forfeit during a regular round:
- Match transitions to `pending_review`.
- `forfeit_by_id` is set to the forfeiting competitor.
- The other competitor is the winner.
- The judge is routed to the review screen for final submission.
- Sudden-death banner is replaced by the standard review screen.

## Score events vs. match results consistency

Two sources of truth need to stay aligned:
- `score_events` — append-only log of every `+1` / `-1`.
- `match_rounds.competitor_a_score` / `competitor_b_score` — derived totals per round.
- `matches.winner_id` — final winner.

### During the match
- `score_events` is the authoritative source.
- `match_rounds` totals are computed from `score_events` on read (no stored running total).
- Cached in-process if needed, invalidated on any score event.

### At submit time
- `match_rounds` rows are *finalized*: `competitor_a_score` and `competitor_b_score` are written to the row from the live computation. This is the snapshot.
- `matches.winner_id` is computed from finalized rounds and stored.

### When admin edits a submitted result
- **Score events are NOT modified** — they're an immutable audit trail.
- `match_rounds` rows are updated to the new values.
- `matches.winner_id` is recomputed and stored.
- Activity log entry: `match.result_edited` with old and new values in `metadata`.
- A note in the admin UI explains: "Original score events from the live match are preserved for audit purposes."

This means: post-edit, the score events on file may not sum to the match's recorded round scores. That's intentional — the events are what the judge clicked, the round scores are what the admin decided was correct.

## Division pause blocks judge actions

When `division.state = 'paused'`:
- Judges cannot **claim** matches in this division (returns 409 with reason).
- Judges cannot **start** scheduled matches (returns 409).
- Judges cannot **start the next round** of an in-progress match (returns 409).
- Already-running rounds continue to tick (don't disrupt mid-round).
- Judges CAN still pause a current round, score, undo, end a round, and submit (allows graceful completion of in-flight matches).

When admin resumes the division:
- All blocked actions become available again.
- No special transition needed for in-progress matches; they just continue.

## Re-subscription idempotency

When a public user re-subscribes to a competitor they previously unsubscribed from:
- The old subscription row is **un-soft-deleted** (`deleted_at = NULL`) rather than creating a new row.
- Same for the web push endpoint — upsert based on `(device_id, participant_id)` unique key.
- Browsers reuse push subscription objects; the `endpoint` URL is stable per-browser per-origin.

This prevents accumulating dead subscription rows over time and ensures push notifications resume immediately on re-subscription.

## Notification deduplication

When admin sends a tournament-wide broadcast, a subscriber following multiple competitors should receive **one** notification, not one per competitor.

- Server fan-out: each `(device_id, broadcast_id)` pair gets exactly one push delivery, regardless of how many participant subscriptions that device has.
- Implemented by deduplicating the recipient list before push dispatch.
- In-app toast: stored with broadcast_id; client shows once per broadcast_id.
