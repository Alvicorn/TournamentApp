# Backlog

## Phased implementation plan

Each phase ends with something demoable. Don't skip phase 1's deploy step — set it up early so you're not debugging deployment under pressure later.

### Phase 1 — Foundations

- [ ] Repo scaffolding (frontend + backend; consider monorepo with pnpm/uv workspaces)
- [ ] Supabase project, Alembic migrations
- [ ] FastAPI app: health check, JWT helpers, Supabase Auth integration
- [ ] `/health/redis` endpoint
- [ ] Redis EC2 provisioning via Terraform (with hardening: `restart: always`, systemd, EC2 auto-recovery)
- [ ] CloudWatch alarms (ALB 5xx, ECS unhealthy tasks, EC2 status checks, CPU credits, Redis health)
- [ ] React app: router, Zustand store skeleton, role-based auth shells
- [ ] Connection status indicator wired up
- [ ] `pytest-bdd` set up with first feature file as proof-of-concept
- [ ] Deploy pipeline to AWS (even if it just serves "hello world") — *do this early, not at the end*
- [ ] Soft-delete utility / mixin for SQLAlchemy models
- [ ] Postgres clock convention enforced via SQLAlchemy `server_default` lint rule

### Phase 2 — Admin core

- [ ] Tournament setup with custom fields + IANA time zone capture
- [ ] Demo / dry-run mode toggle + reset endpoint
- [ ] Judge CRUD + code generation (with checksum)
- [ ] Participant CRUD with custom field rendering
- [ ] Late participant addition (append matches; block after bracket starts)
- [ ] Division CRUD + participant assignment/movement
- [ ] Round-robin generation (even/odd, no bye matches)
- [ ] Match listing + manual reorder
- [ ] Match result editing (round-robin phase only initially)
- [ ] Activity log writes
- [ ] Activity feed view (admin home + dedicated page)
- [ ] Manual backup snapshot button + automated hourly during active

### Phase 3 — Judge flow

- [ ] Judge login (tournament-scoped code, single-device JWT via `jti`)
- [ ] Auto-uppercase + dash-format + client-side checksum validation
- [ ] Onboarding hint card on first match queue view
- [ ] Division picker + match queue
- [ ] Claim/release match (with conflict prevention)
- [ ] Competitor-conflict check on match start (parallel matches in round-robin only)
- [ ] Match start, server-authoritative round timer
- [ ] Pause/resume with `accumulated_paused_seconds` correctness
- [ ] Scoring `+1` / `-1` buttons (equal size)
- [ ] Score idempotency via `client_event_id`
- [ ] Score undo (last 3 events)
- [ ] Forfeit → review screen
- [ ] Sudden-death detection + visual
- [ ] Pre-submit review screen
- [ ] Final submit (with confirmation modal; disabled until final round ended)
- [ ] Reconnect behavior: re-fetch state, never trust cache
- [ ] Offline overlay: "OFFLINE — cannot score"
- [ ] Auto-release background job
- [ ] Admin reassignment endpoint
- [ ] Single-device session: invalidate previous on new login

### Phase 4 — Public views + realtime

- [ ] Public division view (current/next match, standings, live score) — via polling
- [ ] Queue position display ("#N in queue")
- [ ] Parallel match support: 2-up split view, 3+ cycles
- [ ] Pending review state UX ("Match concluded — awaiting submission")
- [ ] Bracket diagram during play-ins/semis/finals
- [ ] SSE infrastructure (FastAPI + Redis pub/sub + Zustand bridge)
- [ ] Standings calculation with tie-break rules (BDD-tested)
- [ ] Standings cache in Redis with proper invalidation
- [ ] Competitor profile page (full match history)
- [ ] Slideshow dashboard (skip empty divisions, no auto-pause)
- [ ] Subscriptions (localStorage device id, in-app toasts)
- [ ] Re-subscribe via upsert (un-soft-delete)
- [ ] Web Push (VAPID, service worker, dispatch with dedup)
- [ ] Admin broadcasts with two-checkbox target selection
- [ ] Connection-lost banner (5s) + overlay (30s)
- [ ] Print-friendly division view (`/divisions/:id/print`)
- [ ] Print-friendly match scorecard (`/matches/:id/print`)
- [ ] Per-IP rate limiting (slowapi)
- [ ] CloudFront 3s edge cache on dashboard endpoint
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
- [ ] Pre-tournament checklist runbook

## Pre-launch operations

- [ ] Document VPC connector setup in IaC
- [ ] Test full backup → restore cycle on staging
- [ ] Test Redis-down runbook (kill EC2; verify recovery)
- [ ] Test bad-edit-recovery runbook
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
- Demo mode resets are admin-only; no version history.
- Supabase free tier limits to 500MB / 50,000 monthly active users — fine for MVP, watch as it grows.
