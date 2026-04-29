# Deployment

## Decision: App Runner + self-hosted Redis on EC2

We chose **AWS App Runner** for the FastAPI backend and **self-hosted Redis on a t4g.nano EC2 instance** for the SSE pub/sub layer.

Cost is the driver. Hardening (below) makes self-hosted Redis production-acceptable for an MVP.

### Why App Runner over EC2 (for the API)

- No OS to patch, no SSH, no disk to monitor.
- Zero-downtime rolling deploys with health-check-based rollback.
- Auto-scales if traffic spikes (e.g., venue projector + 50 phones live).
- Logs and metrics in CloudWatch out of the box.
- Removes ~80% of "tournament day" failure modes for the most critical service.

### Why self-hosted Redis (instead of ElastiCache)

- ElastiCache Serverless minimum is ~$10–15/mo; t4g.nano running Redis is ~$3–4/mo.
- Redis here is **fan-out only** — no critical persistence. If it dies, SSE breaks but core tournament functions survive (public falls back to polling, judges/admin lose realtime until reconnect).
- We compensate for the lack of managed reliability with explicit uptime provisions (see below).

If Redis becomes a recurring pain point, swap to ElastiCache by changing `REDIS_URL` — one-day migration.

## Infrastructure

```
┌─ Route 53 ─┐
│            │
│  tourney   │
│  .com      │
│            │
└──┬──────┬──┘
   │      │
   │      └────► CloudFront ────► S3 (React static build)
   │              [3s edge cache on /tournaments/active/dashboard]
   │
   └─ api.tourney.com ──► AWS App Runner (FastAPI container)
                          │
                          ├─► EC2 t4g.nano (Redis container, hardened)
                          │      via VPC connector, private SG
                          │
                          └─► Supabase Postgres (external)
```

## Components

| Component | Service | Notes |
|---|---|---|
| Frontend hosting | S3 + CloudFront | Static React build; 3s edge cache on dashboard endpoint |
| Backend API | App Runner | FastAPI container from ECR |
| Redis | EC2 t4g.nano (ARM) | Docker, `redis:7-alpine`, password-protected, private SG |
| Database | Supabase | External, free tier viable for MVP |
| Auth (admin) | Supabase Auth | External |
| Backup storage | S3 | Hourly + manual `pg_dump` snapshots |
| DNS | Route 53 | |
| TLS | ACM (CloudFront, App Runner) | Auto-managed |
| Container registry | ECR | For App Runner deploys |
| VPC connector | App Runner → Redis EC2 | Required for private Redis access |
| Logs | CloudWatch | App Runner + EC2 logs aggregated |

## Cost estimate

| Item | Monthly |
|---|---|
| App Runner (1 vCPU / 2GB, mostly idle) | ~$25–35 |
| EC2 t4g.nano (Redis) | ~$3–4 |
| EBS for Redis (8GB gp3) | ~$1 |
| S3 (frontend + backups) | ~$1–3 |
| CloudFront | ~$1 |
| Route 53 | ~$0.50 |
| Supabase | $0 (free tier) |
| **Total** | **~$32–45** |

## Redis uptime provisions

Self-hosting Redis means we own its reliability. Here's the hardening:

### 1. Container-level resilience
`docker-compose.yml` on the EC2 instance:
```yaml
services:
  redis:
    image: redis:7-alpine
    restart: always         # Restarts on container crash
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 100mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data    # Persists across container restarts (not strictly needed for pub/sub)
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "$$REDIS_PASSWORD", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  redis-data:
```

### 2. Host-level resilience
- **systemd unit** ensures Docker Compose comes up on boot:
  ```
  [Unit]
  After=docker.service
  Requires=docker.service
  
  [Service]
  Type=oneshot
  RemainAfterExit=yes
  WorkingDirectory=/opt/redis
  ExecStart=/usr/bin/docker compose up -d
  ExecStop=/usr/bin/docker compose down
  
  [Install]
  WantedBy=multi-user.target
  ```
- **Auto-recovery** for the EC2 itself: configure CloudWatch alarm on `StatusCheckFailed_System` → action: `arn:aws:automate:<region>:ec2:recover`. AWS will automatically migrate the instance to healthy hardware on system failure.
- **Auto-restart on instance failure**: instance launched with "Auto-recovery: enabled".

### 3. Monitoring
- CloudWatch alarm on Redis EC2 CPU credits (t4g.nano is burstable; running out of credits = degraded performance).
- CloudWatch alarm on EC2 status checks (alerts via SNS → email).
- Simple `/health/redis` endpoint in FastAPI that pings Redis; alerted on 5xx.

### 4. Application-level resilience
The FastAPI app must tolerate Redis being temporarily unreachable:
- SSE workers retry connection with exponential backoff.
- If Redis is down, server still serves REST traffic (just no SSE fan-out across workers).
- Public clients automatically fall back to polling, so they're unaffected by Redis outage.
- Judges/admin see "Reconnecting…" indicator until SSE comes back.

### 5. Disaster recovery runbook
If Redis EC2 is unrecoverable, see [`operations.md`](operations.md#redis-down-runbook). 5-minute recovery target.

## Backup strategy (three-layer)

See [`operations.md`](operations.md#backups) for full detail. Summary:

1. **Continuous**: Supabase free-tier daily snapshots (7-day retention). Disaster floor.
2. **Hourly during active tournaments**: Background job runs `pg_dump` → S3 while `tournaments.lifecycle_state = 'active'`. Stops when tournament completes.
3. **Pre-action snapshots**: Server automatically snapshots before risky operations (bracket regen, result edit, lifecycle transitions, late additions). No admin button. Restore is a manual ops procedure, not a UI action.

## CI/CD

GitHub Actions:

### Frontend
1. Install deps, run lint + tests + type check.
2. `vite build`.
3. `aws s3 sync dist/ s3://tourney-frontend/ --delete`.
4. `aws cloudfront create-invalidation --paths "/*"`.

### Backend
1. Install deps, run lint + tests + type check.
2. `docker build` (linux/arm64).
3. `docker push` to ECR.
4. `aws apprunner start-deployment` for the service.

App Runner does the rolling deploy itself with health checks.

### Redis EC2
- Provisioned via Terraform/CloudFormation (one-time).
- No CI/CD; updates done manually via SSH only when explicitly needed.

## Environment configuration

| Variable | Where | Notes |
|---|---|---|
| `DATABASE_URL` | App Runner env | Supabase connection string |
| `REDIS_URL` | App Runner env | `redis://:password@<redis-ec2-private-ip>:6379` |
| `REDIS_PASSWORD` | EC2 + App Runner env | Shared secret |
| `SUPABASE_JWKS_URL` | App Runner env | For verifying admin JWTs |
| `JUDGE_JWT_SECRET` | App Runner env | HS256 secret for judge tokens |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` | App Runner env | Web push |
| `ADMIN_EMAIL_ALLOWLIST` | App Runner env | Comma-separated list |
| `BACKUP_S3_BUCKET` | App Runner env | Where `pg_dump` exports go |
| `AWS_REGION` | App Runner env | For S3 + CloudWatch SDK calls |
| `VITE_API_URL` | GitHub Actions secret | Baked into frontend build |
| `VITE_VAPID_PUBLIC_KEY` | GitHub Actions secret | Baked into frontend build |

## VPC networking note

Redis EC2 sits in a private subnet. App Runner needs a **VPC connector** to reach it. One-time setup:

1. Create a VPC with at least 2 private subnets (or use default + add a NAT gateway-less setup).
2. Launch the t4g.nano EC2 in a private subnet.
3. Security group `redis-sg`: inbound TCP 6379 from `apprunner-sg` only.
4. Security group `apprunner-sg`: outbound TCP 6379 to `redis-sg`.
5. Create an App Runner VPC connector pointing at those subnets + `apprunner-sg`.
6. Attach the VPC connector to the App Runner service.

Document this in your IaC — it's the most easily forgotten setup step.

## Pre-tournament checklist

Run morning of every tournament. Full version in [`operations.md`](operations.md#pre-tournament-checklist).

1. ✅ App Runner service is `Running`.
2. ✅ Redis EC2 is `running` and `2/2 status checks passed`.
3. ✅ `curl https://api.tourney.com/health` returns 200.
4. ✅ `curl https://api.tourney.com/health/redis` returns 200.
5. ✅ Public dashboard loads.
6. ✅ Test admin login.
7. ✅ Test judge code login (throwaway code).
8. ✅ Open public dashboard on the venue projector; verify slideshow ticks.
9. ✅ Verify a test match scores end-to-end via dry-run mode.
10. ✅ Print backup bracket from `/divisions/:id/print`.
11. ✅ Confirm Supabase isn't near free-tier limits.

## Disaster scenarios

| Scenario | Mitigation |
|---|---|
| App Runner crashes | Auto-restarts; deploys are health-checked |
| Redis EC2 dies | CloudWatch alarm fires; auto-recovery migrates to new hardware (~2-5 min). Public falls back to polling. SSE clients reconnect. See runbook in `operations.md` |
| Redis container crashes | `restart: always` brings it back in seconds |
| Supabase down | Application down. No mitigation; rely on Supabase SLA. Print backup is the only recourse |
| Network at venue dies | All clients show disconnected overlay. Print backup; admin can submit results retroactively when network returns |
| VPC connector fails | App Runner can't reach Redis. SSE breaks; public unaffected (polling). Judges/admin lose realtime — fall back to manual refresh. CloudWatch logs |
| Bad admin edit corrupts data | Restore from most recent backup snapshot (manual or hourly) |

## Future infrastructure work

- Move Postgres from Supabase to RDS if Supabase costs grow.
- Consider ElastiCache if Redis on EC2 becomes a recurring pain point.
- Multi-region failover (probably never needed).
- Add proper observability (Sentry, custom metrics) — currently CloudWatch logs only.
