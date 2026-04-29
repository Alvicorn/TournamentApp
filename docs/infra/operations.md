# Operations

This document covers everything you need to know to keep the app running, recover from failures, and prepare for tournament day. Pair with [`deployment.md`](deployment.md) for infrastructure setup.

## Backups

Three-layer strategy. **All backups are automatic** — there's no admin button to push.

### Layer 1: Continuous (Supabase free tier)
- Daily automatic snapshots, 7-day retention.
- No action required. This is the disaster floor.
- Restore via Supabase dashboard.

### Layer 2: Hourly during active tournaments
- FastAPI background job runs **only while** at least one tournament has `lifecycle_state = 'active'`.
- Every hour on the hour, runs `pg_dump` → uploads to S3 bucket `BACKUP_S3_BUCKET`.
- Path: `s3://<bucket>/auto/<tournament_id>/<YYYY-MM-DD-HH>.sql.gz`.
- Retention: 90 days (lifecycle policy on S3 bucket).
- Stops automatically when tournament transitions to `completed`.
- Cost: ~$1/mo for 90 days of hourly dumps from a small DB.

### Layer 3: Pre-action snapshots (automatic, on demand)
- Triggered automatically by the server before any risky operation:
  - Bracket regeneration
  - Editing a submitted result
  - Lifecycle transitions (especially `active → setup`)
  - Late participant additions
- Same `pg_dump` → S3 pipeline, with prefix `pre-action/` and the action name.
- Path: `s3://<bucket>/pre-action/<tournament_id>/<timestamp>-<action>.sql.gz`.
- Retention: indefinite (lifecycle policy moves to S3 Glacier after 30 days).
- Admin sees this in the snapshot list at `/admin/backups` but doesn't trigger them manually.

### Restore process — manual ops procedure
**Restore is not exposed in the admin UI.** It's a deliberate, careful action handled by an engineer with database access. See [bad admin edit runbook](#bad-admin-edit-runbook).

Reasoning: restoring is destructive (overwrites everything since the snapshot). Doing this in front of users mid-tournament under pressure is risky. Better to have an engineer carefully execute via Supabase SQL editor with verification steps.

## Monitoring

We deliberately keep monitoring KISS — CloudWatch logs only, no Sentry, no UptimeRobot.

### What we watch via CloudWatch
- App Runner logs (auto-aggregated).
- EC2 (Redis) status checks.
- EC2 CPU credit balance (t4g.nano is burstable; running out = degraded).
- Custom metric: `redis_health_check_failures` (incremented when `/health/redis` fails).

### Alarms (route to admin email via SNS)
- App Runner: 5xx rate > 5% over 5 minutes.
- EC2: `StatusCheckFailed_System` for >2 minutes → triggers auto-recovery.
- EC2: `StatusCheckFailed_Instance` for >2 minutes → email alert (manual intervention needed).
- EC2: CPU credit balance < 20 → email alert (degradation imminent).
- Redis health check: 3 consecutive failures → email alert.

### Health endpoints
- `GET /health` — overall app health, returns 200 if FastAPI is up + DB reachable.
- `GET /health/redis` — Redis connectivity check, returns 200 if `PING` succeeds.

### What we explicitly DON'T monitor for MVP
- No Sentry / error tracking — CloudWatch logs are enough for post-mortem.
- No external uptime monitoring (UptimeRobot, etc.).
- No custom dashboards or SLOs.
- No real user monitoring (RUM).

These are all candidates for post-MVP. Add when pain demands it.

## Rate limiting

Rate limits applied at the FastAPI level using `slowapi` or similar. Per-IP buckets.

| Surface | Limit | Reasoning |
|---|---|---|
| Public endpoints (dashboard, division view, etc.) | 60 req/min per IP | Polling = 20/min baseline; gives 3x headroom |
| Subscriptions endpoints (POST/DELETE) | 30 req/min per IP | Prevents subscription spam |
| Admin login | 5 attempts per 15 min per IP | Prevents brute force |
| Judge login | 5 attempts per 15 min per IP | Prevents brute force on codes |
| All other admin endpoints | 600 req/min per IP | Generous; admin shouldn't hit this |
| All other judge endpoints | 600 req/min per IP | Score events can be rapid; need headroom |
| SSE connection | 5 per IP | Prevents connection-bombing |

### Edge caching as defense-in-depth
- CloudFront caches `GET /tournaments/active/dashboard` for **3 seconds** at the edge. Same poll interval as the client.
- Cache key includes `X-Device-Id` (so per-device subscription state isn't leaked).
- This means 1000 phones polling once every 3s = ~1 origin request per 3s, not 333/s.

### Response on rate limit hit
- Return `429 Too Many Requests` with `Retry-After` header.
- Client toast: "Too many requests, slowing down…"
- Logged in CloudWatch for review.

## Pre-tournament checklist

Run the morning of every tournament. **All steps must pass.**

### Infrastructure
- [ ] App Runner service is `Running` in AWS console.
- [ ] Redis EC2 is `running` with `2/2 status checks passed`.
- [ ] Supabase project status: green.
- [ ] No active CloudWatch alarms.

### Connectivity
- [ ] `curl https://api.tourney.com/health` → 200
- [ ] `curl https://api.tourney.com/health/redis` → 200
- [ ] `curl https://tourney.com/` → 200 (frontend)

### Functional smoke test
- [ ] Admin login works.
- [ ] Judge login works (with throwaway code).
- [ ] Public dashboard loads.
- [ ] Slideshow ticks through divisions.
- [ ] Test match scores end-to-end in dry-run mode.

### Backup readiness
- [ ] Supabase nightly backup confirmed.
- [ ] Verify hourly backup job is enabled (will start once tournament goes `active`).
- [ ] Verify pre-action snapshot job is functional (trigger a no-op test action and confirm S3 write).

### Venue prep
- [ ] Print bracket backup from `/divisions/:id/print` for each division.
- [ ] Open public dashboard on venue projector; verify rendering.
- [ ] Confirm reliable network at venue.
- [ ] Have a second person who can SSH into the Redis EC2 if needed.

## Runbooks

### Redis-down runbook
**Symptom**: `/health/redis` returns 5xx; CloudWatch alarm fires; SSE clients show disconnected.

**Triage** (first 60 seconds):
1. Check EC2 console: is the instance `running`?
2. If `stopped`: start it. Auto-recovery should have done this; if not, do it manually.
3. If `running` but unreachable: SSH in and check `docker ps`.

**Common fixes**:
- **Container died**: `docker compose up -d` from `/opt/redis`.
- **Out of disk**: `docker system prune -af` then restart.
- **Network/SG misconfigured**: check security group; should allow 6379 from App Runner's SG.

**If unrecoverable** (5+ minutes):
- Application **continues to work** — public users polling, judges/admin can manually refresh.
- Public falls back to polling automatically.
- Judges/admin see "Reconnecting…" indicator; SSE will reconnect when Redis returns.
- Provision a new EC2 from the Terraform/CloudFormation template (~5 min).
- Update `REDIS_URL` env var on App Runner.
- Trigger App Runner deployment to pick up new env.

**Don't panic**: Redis is fan-out only. No tournament data is at risk.

### Stuck match runbook
**Symptom**: Admin reports a judge claimed a match, then disappeared (phone dead, walked away, etc.).

**Resolution**:
1. Admin opens the division detail page.
2. Finds the stuck match (state = `paused` or `in_progress`).
3. Clicks "Reassign Judge" → selects new judge.
4. Match state becomes `paused`; new judge can resume.
5. If match was `in_progress`, the round timer's `accumulated_paused_seconds` is updated to reflect the time since auto-pause.

**If admin isn't available**: auto-release fires after 10 minutes of inactivity (paused matches only). The match returns to `scheduled` and any judge can claim it.

### Bad admin edit runbook
**Symptom**: Admin made a change they regret (deleted a participant, edited wrong result, regenerated bracket prematurely).

**Resolution** (engineer, not admin):
1. **Stop further edits immediately.** Pause the affected division via admin UI.
2. Identify the most recent **pre-action snapshot** or hourly backup before the bad edit (S3 console).
3. Download the dump.
4. **Take a fresh snapshot** of current (broken) state via Supabase dashboard, in case restore goes wrong.
5. In Supabase SQL editor, restore the dump to a **scratch schema** first (e.g., `restore_test`).
6. Verify the restored state has the data you want.
7. If correct, apply the restore to the production schema. **This overwrites everything since the snapshot.**
8. Verify in admin UI; resume division.

**Time to recover**: ~10 minutes if backups are recent. Requires engineer access — not an admin self-service action.

### Tournament data corruption / inconsistency runbook
**Symptom**: Standings don't add up, match results contradict round events, etc.

**Resolution**:
1. Check the activity log for recent admin/judge actions.
2. Take a manual snapshot via Supabase dashboard (engineer action).
3. Use the API directly (or Supabase SQL editor) to inspect:
   - `score_events` for the suspect match
   - `match_rounds` rows
   - `matches.winner_id` vs computed winner
4. If recoverable: edit the offending match via admin UI (with confirmation modal warning).
5. If not: restore from backup as in the bad-edit runbook.

### Network outage at venue runbook
**Symptom**: All clients show "Disconnected" overlay. App is unreachable.

**Resolution**:
1. Tournament continues on paper.
2. Use the printed bracket as the source of truth.
3. When network returns, admin manually enters scores from paper into the affected matches via the edit-result endpoint.
4. Subscribers automatically reconnect; standings recompute.

This is why the print-friendly view is a real feature, not a nice-to-have.

## Logging

CloudWatch log groups:

- `/aws/apprunner/tourney-api/application` — FastAPI logs.
- `/aws/apprunner/tourney-api/service` — App Runner platform logs (deploys, health).
- `/ec2/redis-host/system` — EC2 system logs (via CloudWatch agent).
- `/ec2/redis-host/docker` — Docker container logs.

### What we log at INFO
- All admin actions (also written to `activity_log` table).
- All judge actions (claim, score, submit, forfeit) — also in `activity_log`.
- Tournament lifecycle transitions.
- SSE connection lifecycle.
- Background job runs (auto-release, backup).

### What we log at ERROR
- Unhandled exceptions.
- Failed backup uploads.
- Redis connection failures.
- Auth failures (with rate-limit context).

### What we DON'T log
- PII beyond what's already public (participant names are public; that's fine).
- Full request bodies on score events (high volume, low value).
- Health check pings.

## Tournament lifecycle operations

### Starting a tournament (`setup → active`)
- Admin clicks "Start Tournament" with confirmation modal.
- Pre-flight check: ≥1 division with ≥2 participants. If not, block with clear error.
- Custom field spec freezes.
- Hourly backup job starts.
- Activity log entry: `tournament.activated`.

### Completing a tournament (`active → completed`)
- Admin clicks "Complete Tournament" with confirmation modal.
- Pre-flight check: all divisions are `completed` or admin acknowledges incomplete divisions.
- Hourly backup job stops.
- Final manual snapshot taken automatically.
- Public view becomes read-only (URLs still work forever).
- Subscribers receive a tournament-wide "Tournament complete — congratulations to medal winners" notification (non-personalized).
- Activity log entry: `tournament.completed`.

### Reverting (`active → setup`)
- Admin can force back to `setup` for emergency corrections.
- Hard warning modal: "This will unfreeze the custom field spec and may affect existing participant data."
- Type `REVERT` to confirm.
- Hourly backup job stops.
- Activity log entry: `tournament.reverted_to_setup`.
