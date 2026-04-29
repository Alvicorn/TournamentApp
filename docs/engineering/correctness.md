# Correctness Guarantees

This document captures the correctness-critical behaviors that are easy to get wrong and where bugs would cause real-world damage (invalid results, frozen scoreboards, misattributed wins).

## Timer authority

**The server is the authoritative source of round time.** The client only displays time; it never decides time.

### Single clock: Postgres `now()`
All server-side timestamps come from Postgres `now() AT TIME ZONE 'utc'`, **not** Python's `datetime.utcnow()`. This avoids drift between FastAPI process clocks (which can vary across App Runner workers) and the database. SQLAlchemy `server_default=func.now()` handles inserts; explicit `now()` in UPDATE statements handles modifications.

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

## Score idempotency

Network retries must not double-count. Misclicks must be undoable.

### Idempotency
Each score event from the client carries a `client_event_id` (UUID). Server dedupes on `(match_id, client_event_id)` via unique index. A retry with the same id returns the same response without applying the delta a second time.

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

Judges can lose network mid-match (Wi-Fi flaps, phone sleeps, etc.).

### On page load
1. Fetch judge's current claimed match from server.
2. Fetch full match state including all rounds and current scores.
3. Reconnect SSE.
4. If the judge's previously-claimed match was auto-released or reassigned, show a toast and route to the division match queue.

### On SSE reconnect
1. Re-fetch match state (full snapshot, not delta).
2. Replace local Zustand state.
3. Resume listening.

**Never trust local state after a connection gap.** SSE reconnects use `Last-Event-ID` if you want to be fancy, but for MVP a full re-fetch is simpler and sufficient.

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

When the judge's device is offline (no network, browser detects), scoring is **disabled entirely**. No queueing, no optimistic updates.

### Detection
- Browser's `navigator.onLine` + active fetch failures.
- After 1 failed score event request → assume offline → show overlay.

### UI behavior
- Full-screen overlay on the scoring screen: **"OFFLINE — cannot score"**.
- Buttons (`+1`, `-1`, undo, pause/resume, end round, submit) all disabled.
- Round timer continues to display (server-authoritative time recovers on reconnect).
- Toast on reconnect: "Back online. You can resume scoring."

### Why not queue offline scores?
- Queueing introduces conflict resolution complexity.
- Score timing matters in martial arts (a point at 0:30 vs 0:31 may matter for video review).
- Better to require the judge to wait for network than to silently mis-record events.

### Recovery
- On reconnect, client re-fetches full match state from server (per [reconnect behavior](#reconnect-behavior-judges)).
- Local state is discarded.
- Judge resumes scoring with confirmed server state.

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
- Cached in Redis if needed, invalidated on any score event.

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
