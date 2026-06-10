# Frontend

## Stack

- **React** + **TypeScript**
- **Tailwind CSS**
- **Zustand** for state (chosen over Redux for simplicity; this app's state is small)
- **TanStack Query** (React Query) for API calls + caching + invalidation
- Custom SSE hook (`useSSE(url)`) — wraps `EventSource` and feeds events into Zustand stores
- Service Worker (via `vite-plugin-pwa`) for Web Push **and** offline app-shell caching (judge scoring must survive a refresh while offline)
- **Vite** for build tooling

## Why Zustand?

The original spec called for Redux Toolkit. We switched because:
- This app's global state is small (~8 logical stores).
- Zustand is ~1KB vs Redux's ~10KB+.
- Less boilerplate; clearer for new contributors.
- TanStack Query already handles server state (the bulk of "Redux"-shaped concerns).

## Routes

```
/                           → public dashboard (slideshow)
/divisions/:id              → public division view
/divisions/:id/print        → print-friendly bracket / standings (CSS @media print)
/competitors/:id            → public competitor profile
/matches/:id/print          → print-friendly match scorecard
/subscriptions              → manage my subscriptions (device-scoped)

/admin/login
/admin                      → admin home (tournament status + activity feed)
/admin/setup                → tournament config (visible during setup state)
/admin/judges
/admin/participants
/admin/divisions
/admin/divisions/:id        → division detail (matches, controls)
/admin/broadcasts
/admin/backups              → snapshot list (view-only)
/admin/activity             → full activity log view

/judge/login
/judge                      → division picker + my active match shortcut
/judge/divisions/:id        → match queue (claim, reorder, start)
/judge/matches/:id          → scoring screen (active match)
/judge/matches/:id/review   → pre-submit review
```

## State stores (Zustand)

| Store | Purpose |
|---|---|
| `useAuthStore` | Current user, role, JWT |
| `useTournamentStore` | Active tournament config |
| `useLiveScoreStore` | Driven by SSE; keyed by matchId |
| `useOutboxStore` | Judge offline outbox: queued score events + round commands, persisted to IndexedDB; pending count drives the offline banner |
| `useSubscriptionsStore` | Public, hydrated from localStorage + API |
| `useNotificationsStore` | Toast queue |
| `useUIStore` | Slideshow index, modals, connection status |

Server state (judges list, participants list, divisions, matches as resources) lives in **TanStack Query**, not Zustand. Zustand is only for client-driven or push-driven state.

## UX guardrails

The judge scoring screen is the highest-stakes UI in the app. A misclick during a live match is worse than any other bug.

### Judge scoring screen
- Huge `+1` and `-1` buttons (**equal size and prominence**) for thumb use on phone in chaotic gym lighting.
- Big timer, big score numbers.
- **Color zones**: positional, per-match (competitor_a = red, competitor_b = blue). Color is reinforced with text labels and screen position; never the only signal.
- **Submit button disabled** until the final round has ended.
- **Confirmation modal** on submit (irreversible from judge side).
- **Recent score history** with undo buttons for the last 3 events. Idempotent retry via `client_event_id`.
- **Forfeit button** routes to review screen (does not submit directly).
- **Round transition**: when a round ends, show explicit "Round N+1 ready — tap to start" full-width button. Never auto-advance.

### Result display rules
When showing a finished match's result anywhere (public view, competitor profile, etc.):
- Standard match: `"Alice def. Bob 5-3 in 3 rounds"`
- Sudden-death match: `"Alice def. Bob 6-5 in sudden-death"` (no numeric round count)
- Forfeit: `"Alice def. Bob (forfeit)"` (no score, no rounds)

### Sudden-death visual

When a match enters sudden-death, the judge scoring screen displays:
- Full-screen pulsing red border (subtle animation — `animate-pulse` slowed).
- Large header: **"SUDDEN DEATH"**.
- Subtext below score area: **"Next point wins"**.
- Round timer disappears (no time limit).
- The next score event (whichever competitor) ends the match → moves to review.

### Public slideshow
- Full-screen mode (`requestFullscreen` on user gesture).
- High contrast, designed for venue projection.
- Gold/bronze slides use the **same duration** as every other slide (no auto-pause); they only differ via a special icon (e.g., 🥇 / 🥉).
- Skip slides for divisions with no active match.
- **Parallel matches**: if a division has 2 simultaneous matches, slide shows split view; 3+ cycles them as separate sub-slides for that division.
- **During bracket phases** (play-ins/semis/finals/bronze): slide shows the current bracket match prominently AND a small bracket diagram on the side instead of full standings (since standings are now baked into the bracket position).
- **Pending review state**: when a match is scored but not yet submitted, slide shows the match with a "Match concluded — awaiting submission" overlay instead of live scores. Prevents confusing the audience.
- **Connection lost banner**: small, top of screen, after 5s without successful poll.
- **Disconnected overlay**: full-screen, after 30s of failure. Audience needs to know not to trust scores.

### Public division view
- Shows current match(es), upcoming queue, and standings.
- **Parallel matches** in round-robin: shown stacked, with clear "currently playing" markers on each.
- Each upcoming match displays its **queue position** ("#3 in queue"). No time estimates.
- Shows live score for in-progress matches. Shows "Concluded — awaiting submission" for matches in `pending_review`.
- Standings update on poll (not realtime SSE).
- During bracket phases: shows the bracket diagram alongside (or replacing) standings, with the live match highlighted.
- Linked from public dashboard slideshow.
- "Print bracket" link sends to `/divisions/:id/print`.

### Public competitor profile
- Lists all the competitor's matches and outcomes.
- Per-match: opponent, final score, win/loss, round count.
- **Public-safe data only**: no per-round scores.
- Subscribe / unsubscribe button at the top.

### Admin tables
- Dense, keyboard-friendly.
- Inline edit where possible.
- **Desktop-only**: admin routes show a "Please use a desktop" message on viewports < 1024px wide. KISS.

### Admin activity feed
- Real-time pane on admin home + dedicated `/admin/activity` view.
- Filter by division, actor, action type.
- Powered by `GET /sse/activity` — see [`backend.md`](backend.md#sse-streams).
- Examples: "Judge Maria claimed Match 12", "Match 12 submitted: Alice def. Bob 5-3", "Division Heavyweight paused: ring 3 unavailable".

### Admin broadcasts
Admin selects target audience via two independent checkboxes:
- ☐ **Subscribers** — sends toast on devices subscribed to any competitor in this tournament + tournament-wide subscribers. Web Push for tab-closed devices.
- ☐ **Public dashboard** — banner at top of public dashboard for everyone viewing.

Send button disabled until at least one box is checked. Recent broadcasts listed for review. UI shows a clear preview before sending.

Notification deduplication: a subscriber following 5 competitors receives **one** toast per broadcast, not five. See [`correctness.md`](correctness.md#notification-deduplication).

### Admin "preview as" mode
A dropdown in the admin nav: **Preview as → [Public | Judge]**. Clicking opens a new tab pointed at the relevant view, with the admin's session preserved. Useful for spot-checking what users see during a live tournament.

- "Public" preview: opens `/` in a new tab. No session token needed (public is unauthenticated).
- "Judge" preview: opens `/judge` in a new tab with a special read-only judge token (no claims/scores possible). Confirms layout but won't disrupt actual judges.

This is read-only diagnostic, not impersonation.

### Backup management (admin)
- Tournament settings page shows: **"Last automatic snapshot: 14 minutes ago"** (read-only status indicator).
- **No "Snapshot Now" button.** Snapshots are taken automatically before any risky operation (regenerate bracket, edit submitted result, lifecycle transition, late participant addition). The system does this; the admin doesn't think about it.
- **No restore-from-UI.** Restore is a manual ops procedure handled by an engineer with database access. See [`deployment.md`](deployment.md#backups). This is intentional — restore should never happen in front of users mid-tournament; it's a deliberate, careful action.
- Snapshot list visible at `/admin/backups` for transparency: shows timestamps, what triggered each, and download links. View-only.

### Unclaimed match alert
On admin home, if more than 3 round-robin matches are unclaimed and the tournament has been active for more than 15 minutes, show a yellow banner: **"5 matches across 2 divisions are unclaimed. You may need more judges."** Helps spot judge shortages in real time.

### Web push registration
- Prompt only after the user explicitly subscribes to *something* (never on page load — that's an anti-pattern).
- One-time prompt; if denied, don't re-prompt automatically.

### Print-friendly views
- `/divisions/:id/print` — bracket + standings (used as paper backup if network fails).
- `/matches/:id/print` — individual match scorecard with round-by-round scores. Useful for archives, dispute review.
- Both use CSS `@media print` rules: no nav, no animation, high contrast for printing.
- Linked from public division view as "Print bracket" and from match detail views as "Print scorecard".

## Judge reconnect behavior

- On page load AND on SSE reconnect: **flush the offline outbox first, then re-fetch match state from server**. Flushing first means the snapshot already includes the judge's offline work — see [`correctness.md`](correctness.md#reconnect-behavior-judges).
- Never trust client cache after a network gap (the outbox is the one exception — it's the record of what the server hasn't seen).
- If the judge's claimed match has been auto-released or reassigned, show a clear toast: "Your match was reassigned. View other available matches." If the outbox had pending events, surface them per the conflict UX below — never discard silently.

## Judge offline banner

Scoring continues offline — see [`correctness.md`](correctness.md#judge-offline-scoring) for the design. When the device goes offline (`navigator.onLine = false` or a request fails):

- **Non-blocking amber banner** at the top of the scoring screen: **"Offline — scoring saved on this device"**, with a pending-events badge ("4 pending sync").
- All scoring and round-control buttons (`+1`, `-1`, undo, pause/resume, end round) **stay enabled**; actions append to the outbox and update the UI optimistically.
- **Submit stays disabled while offline** (and until the outbox is drained), with helper text "Reconnect to submit".
- Round timer keeps running locally (it derives from timestamps; no server needed).
- On reconnect: outbox flushes, banner dismisses, toast **"Back online — N events synced."**

### Conflict UX (match reassigned while offline)
If the flush is rejected because the match was reassigned or the judge removed:
- Modal: "This match was reassigned while you were offline. Your **N** recorded events were NOT submitted."
- The modal lists the unsent events (time, competitor, ±1) so the score can be reconstructed with the admin.
- Events remain viewable from the match queue until dismissed explicitly.

### PWA app shell
- `vite-plugin-pwa` precaches the app shell so a refresh or accidental tab close while offline returns to a working scoring screen (outbox and last match snapshot persist in IndexedDB).
- Judge instruction stays simple: you don't need to avoid refreshing, but don't switch devices while offline (sessions are single-device).

## Judge multi-device

Sessions are bound to a single device via JWT `jti` (see [`correctness.md`](correctness.md#judge-multi-device-sessions)).

- If a judge logs in elsewhere, the previous device's next API call returns 401.
- Toast on previous device: "Logged in from another device. Please log in again to continue."
- Auto-redirect to login screen.
- This is intentional UX: judges shouldn't be on two devices at once during a match.

## Empty states

Each major surface has a lightweight empty state. Keep these brief.

| Surface | Empty state copy |
|---|---|
| Public dashboard, no active tournament | "No tournament is currently running. Check back soon." |
| Public division, no matches | "Matches haven't been scheduled yet." |
| Public division URL not found | "Division not found. Return to dashboard." |
| Judge match queue (no matches) | "No matches available. Check back when admin has scheduled some." |
| Judge match queue (all matches in conflict) | "All matches are waiting on competitors in other matches." |
| Admin home, no tournament | "Get started by creating your first tournament." with CTA |
| Admin participants list, empty | "Add your first participant to get started." with CTA |
| Admin divisions list, empty | "Create a division to organize your participants." with CTA |
| Activity feed, no recent activity | "No activity yet. Actions will appear here as the tournament runs." |
| Subscriptions page (public), empty | "You're not subscribed to anyone yet. Tap a competitor to subscribe." |

## Login UX

### Judge login
- Single field: code input.
- Auto-uppercases as user types.
- Auto-formats with mid-string dash for readability: `ABCD-EFGH1`.
- Validates checksum client-side before submitting (prevents wasted server roundtrip on typos).
- Error states: "Code not recognized" (generic — don't leak whether prefix exists).
- Helper text: "Get your 8-character code from the tournament admin."

### Admin login
- Email + password fields.
- Standard Supabase Auth flow.
- "Forgot password?" link to Supabase reset flow.

## Logout

- Visible logout button in header for judges and admins.
- Clears local state, JWT, and revokes server-side session (for judges, sets `current_session_jti = null`).
- Public users have no logout (no session); they can clear their device subscriptions via `/subscriptions`.

## Session length

- Judge JWT: 24 hours from login. Covers multi-day tournaments without re-login mid-event.
- Admin JWT: Supabase default (typically 1 hour with refresh).

## Onboarding helper text

The judge match queue page has a single line of helper text above the queue:

> **Tap a match to claim it. Greyed-out matches have a competitor already playing elsewhere.**

Always visible, no localStorage state, no dismiss action. KISS.

## 404 / not found

Simple page: "We couldn't find what you were looking for." with button "Return to dashboard".

## Connection status indicator

A small status pill in the corner of every page:
- 🟢 Live — SSE connected (or polling succeeding)
- 🟡 Reconnecting — < 30s since last successful update
- 🔴 Disconnected — > 30s; for public dashboard, also show full-screen overlay
- 🟠 Offline — N pending — judge scoring screen only: device offline with N outbox events awaiting sync (mirrors the offline banner)

## Theming / accessibility

- WCAG AA contrast minimum on all surfaces.
- Touch targets ≥ 44px on judge UI.
- Keyboard navigation on admin UI.
- Color is **never the only signal** (sudden death uses border + text + position, not just red).
