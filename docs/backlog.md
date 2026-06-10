# Backlog

## Phased implementation plan

Each phase ends with something demoable. Don't skip phase 1's deploy step — set it up early so you're not debugging deployment under pressure later.

### Phase 1 — Foundations

- [x] Repo scaffolding (frontend + backend; consider monorepo with pnpm/uv workspaces)
- [x] Supabase project, Alembic migrations
- [x] FastAPI app: health check, JWT helpers, Supabase Auth integration
- [x] React app: router, Zustand store skeleton, role-based auth shells
- [x] Connection status indicator wired up
- [x] `pytest-bdd` set up with first feature file as proof-of-concept
- [x] Deploy pipeline (even if it just serves "hello world") — *do this early, not at the end*; retargeted from AWS to Render 2026-06
- [x] Soft-delete utility / mixin for SQLAlchemy models
- [x] Postgres clock convention enforced via SQLAlchemy `server_default` lint rule
- [ ] Set up UptimeRobot monitor on `/health` (keep-awake + alerting)
- [ ] Create Cloudflare R2 bucket + credentials for backups

### Phase 2 — Admin core

- [ ] Tournament setup with custom fields + IANA time zone capture
- [ ] Demo / dry-run mode toggle (reset = delete + recreate; no reset endpoint)
- [ ] Judge CRUD + code generation (with checksum)
- [ ] Participant CRUD with custom field rendering
- [ ] Late participant addition (append matches; block after bracket starts)
- [ ] Division CRUD + participant assignment/movement
- [ ] Round-robin generation (even/odd, no bye matches)
- [ ] Match listing + manual reorder
- [ ] Match result editing (round-robin phase only initially)
- [ ] Activity log writes
- [ ] Activity feed view (admin home + dedicated page)
- [ ] Automated hourly backups while tournament is active (no manual snapshot button — all backups automatic)

### Phase 3 — Judge flow

- [ ] Judge login (tournament-scoped code, single-device JWT via `jti`)
- [ ] Auto-uppercase + dash-format + client-side checksum validation
- [ ] Single-line onboarding helper text above match queue (always visible; no hint card, no localStorage)
- [ ] Division picker + match queue
- [ ] Claim/release match (with conflict prevention)
- [ ] Competitor-conflict check on match start (parallel matches in round-robin only)
- [ ] Match start, server-authoritative round timer
- [ ] Pause/resume with `accumulated_paused_seconds` correctness
- [ ] Round-control commands idempotent via `client_command_id` + `occurred_at` (`match_commands` table)
- [ ] Scoring `+1` / `-1` buttons (equal size)
- [ ] Score idempotency via `client_event_id` + `client_recorded_at`
- [ ] Score undo (last 3 events)
- [ ] Forfeit → review screen
- [ ] Sudden-death detection + visual (incl. deterministic offline entry)
- [ ] Pre-submit review screen
- [ ] Final submit (with confirmation modal; disabled until final round ended AND outbox drained)
- [ ] Offline outbox store (IndexedDB persistence, write-through when online, ordered flush)
- [ ] Offline banner + pending-sync badge (buttons stay enabled; submit disabled)
- [ ] Reconnect behavior: flush outbox, then re-fetch state
- [ ] Conflict UX: reassigned-while-offline modal with unsent-events list (never silently discard)
- [ ] PWA service worker (`vite-plugin-pwa`): app shell survives refresh while offline
- [ ] Auto-release background job
- [ ] Admin reassignment endpoint
- [ ] Single-device session: invalidate previous on new login

### Phase 4 — Public views + realtime

- [ ] Public division view (current/next match, standings, live score) — via polling
- [ ] Queue position display ("#N in queue")
- [ ] Parallel match support: 2-up split view, 3+ cycles
- [ ] Pending review state UX ("Match concluded — awaiting submission")
- [ ] Bracket diagram during play-ins/semis/finals
- [ ] SSE infrastructure (FastAPI in-process pub/sub + `?token=` auth + Zustand bridge)
- [ ] Standings calculation with tie-break rules (BDD-tested)
- [ ] Standings cache (in-process, TTL) with proper invalidation
- [ ] Competitor profile page (full match history)
- [ ] Slideshow dashboard (skip empty divisions, no auto-pause)
- [ ] Subscriptions (localStorage device id, in-app toasts)
- [ ] Re-subscribe via upsert (un-soft-delete)
- [ ] Web Push (VAPID, service worker, dispatch with dedup)
- [ ] Admin broadcasts with two-checkbox target selection
- [ ] Connection-lost banner (5s) + overlay (30s)
- [ ] Print-friendly division view (`/divisions/:id/print`)
- [ ] Print-friendly match scorecard (`/matches/:id/print`)
- [ ] Rate limiting (slowapi): per-device keying on public endpoints, per-IP on logins
- [ ] In-process 3s cache on dashboard endpoint (device-neutral response)
- [ ] Empty state copy throughout
- [ ] Result display format: standard / sudden-death / forfeit variants

### Phase 5 — Bracket + polish

- [ ] Play-in generation logic (only tied competitors that affect top-4)
- [ ] Bracket advancement (semis → finals/bronze)
- [ ] Tiny-division handling (<4 competitors)
- [ ] Pause/resume division (with judge action blocking)
- [ ] Admin result correction → tiered behavior (record-only vs regenerate)
- [ ] Score events preserved on result edit (audit trail)
- [ ] "Result corrected" notifications to subscribers
- [ ] Special icons on gold/bronze in public dashboard
- [ ] Pre-action snapshot system (auto-trigger before risky ops)
- [ ] `/admin/backups` view-only snapshot list
- [ ] Post-tournament read-only enforcement
- [ ] Tournament-completion notification to subscribers
- [ ] Admin "Preview as" dropdown (Public + read-only Judge token)
- [ ] Unclaimed-matches alert banner on admin home
- [ ] Final QA, error states, empty states, mobile polish (judge UI)
- [ ] Write pre-tournament checklist (event-day procedure; lives outside docs/ — docs are dev-only)

## Pre-launch operations

- [ ] Test full backup → restore cycle on staging (R2 dump → scratch schema; see `deployment.md#backups`)
- [ ] Test backend-down recovery (suspend Render service; verify restart + judge offline scoring keeps working)
- [ ] Test bad-edit recovery (restore an R2 dump to a scratch schema, verify, apply)
- [ ] Offline scoring sync drill (airplane mode mid-match; score; pause/resume; end round; reconnect; verify server state)
- [ ] Verify Supabase project isn't paused (free tier pauses after ~1 week idle) — recurring pre-event task
- [ ] Load test with Locust (100 concurrent SSE)
- [ ] Run a full dry-run tournament in demo mode

## Future work (post-MVP)

Explicitly **not** in MVP. Prioritized roughly by likely value.

| Feature | Notes |
|---|---|
| Multi-judge scoring per match | Common in sanctioned events; needs averaging/median rules |
| Multiple concurrent tournaments | Currently one active at a time |
| Official PDF results export | Tournament organizers want a deliverable |
| Spectator stats analytics | "View the most exciting matches" type features |
| Internationalization | Translation framework + extracted strings |
| Email/SMS notifications | Email is achievable; SMS is expensive |
| Live video integration | Embed YouTube live stream per division |
| Advanced bracket formats | Double-elimination, Swiss, single-elimination |
| Mobile apps | Native iOS/Android instead of PWA |
| Federation / multi-org | Single tournament app serving multiple organizations |
| Spectator commenting | Slippery slope; moderation cost |

## Known limitations of MVP

- Single judge per match means a stuck match requires admin intervention.
- Polling-based public view may have 3–5s latency for spectators.
- Web push is best-effort; some browsers/devices won't deliver reliably.
- Demo "reset" is delete + recreate; no version history.
- Supabase free tier limits to 500MB / 50,000 monthly active users — fine for MVP, watch as it grows. Free tier also **pauses idle projects after ~1 week** — check the dashboard days before an event.
- Backend is a single instance with a single worker (by design — in-process pub/sub and caches). Scaling out requires reintroducing a broker; see `architecture.md`.
- Render free tier cold-starts after 15 min idle; mitigated by UptimeRobot keep-awake pings.
- Offline judge scoring can be rejected on sync if an admin reassigned the match meanwhile; events are surfaced for manual recovery, not auto-merged.

## Open design questions (found in doc review, 2026-06)

Not yet designed; resolve before the relevant phase starts.

| Question | Affects | Phase |
|---|---|---|
| "Match start" notifications to subscribers are promised in user stories, but no dispatch path / event list is documented (only broadcast, result-corrected, tournament-complete pushes are specified) | Web push fan-out | 4 |
| Sudden-death data model: how is the extra round represented (`round_number = N+1`? what does `round_length_seconds` mean for it)? | `match_rounds`, scoring | 3 |
| Play-in generation for 3+ tied competitors: "single elimination until exactly 4 remain" doesn't specify pairing, seeding, or byes | Bracket logic | 5 |
| Claimed-but-never-started matches never auto-release (scan covers only `paused`); a judge who claims and walks away leaves the match assigned until admin intervenes | Auto-release job | 3 |
| `DELETE /subscriptions/{id}` needs a documented ownership check (verify `X-Device-Id` matches the row) | Subscriptions API | 4 |
| Admin "preview as judge" token isn't tied to a judge row — how does the auth dependency skip the `jti` single-session check? | Auth | 5 |
| `tournaments.time_zone` is captured but no surface specifies what renders in tournament-local time | Display | 2+ |
| On admin reassignment of an `in_progress` match, the match auto-pauses — how `accumulated_paused_seconds` is adjusted for the gap is unspecified in `correctness.md` | Timer | 3 |
| `updated_at` exists on `tournaments` but not on judges/participants/divisions/matches — intentional? | Schema | 2 |
