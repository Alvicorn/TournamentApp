# Deployment

## Decision: ECS Express Mode + self-hosted Redis on EC2

We chose **Amazon ECS Express Mode** for the FastAPI backend and **self-hosted Redis on a t4g.nano EC2 instance** for the SSE pub/sub layer.

### What is ECS Express Mode?

A simplified API on top of standard ECS (launched November 2025) that auto-provisions a production-ready stack from three inputs: a container image, a task execution role, and an infrastructure role. It creates:

- A Fargate-based ECS service
- An Application Load Balancer with HTTPS / SSL/TLS termination
- Auto-scaling policies (CPU-based default; configurable)
- CloudWatch monitoring and alarms
- Security groups with least-privilege rules
- A unique URL on the `*.ecs.<region>.on.aws` domain

When the app eventually needs more advanced ECS features (sidecars, custom auto-scaling metrics, blue-green deploys), those are still available — Express Mode coexists with standard ECS APIs.

### Why ECS Express Mode over App Runner

- **Lower cost**: ~$15–20/mo vs. App Runner's ~$25–35/mo for similar workload sizes.
- **VPC-native**: Tasks run in our VPC by default. Direct intra-VPC connection to the Redis EC2 — no separate VPC connector hop.
- **Standard ECS underneath**: When we outgrow Express Mode's defaults, we can use the full ECS API on the same service without migrating.
- **Same deploy ergonomics**: `update-express-gateway-service` with a new image — just as simple as App Runner from a CI/CD perspective.
- Same operational properties we wanted from App Runner: rolling deploys with health checks, no OS to patch, no SSH, auto-scaling, CloudWatch logs out of the box.

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
   └─ api.tourney.com ──► ALB (provisioned by ECS Express Mode)
                          │
                          └─► Fargate task: FastAPI container
                                 │
                                 ├─► EC2 t4g.nano (Redis container, hardened)  [SSE pub/sub fan-out]
                                 │      same VPC, private SG
                                 │
                                 └─► Supabase Postgres (external)
```

### Custom domain wiring

Express Mode services come with a `*.ecs.<region>.on.aws` URL. To use `api.tourney.com`:

1. Note the ALB DNS name from the Express Mode service.
2. In Route 53, create an A-record alias for `api.tourney.com` pointing at that ALB.
3. Issue an ACM certificate for `api.tourney.com` and attach it to the ALB listener (this is a one-time direct ECS/ALB action; Express Mode doesn't manage custom domains itself).

After this, both URLs work; we use `api.tourney.com` everywhere in client code and ignore the AWS-provided URL.

## Components

| Component | Service | Notes |
|---|---|---|
| Frontend hosting | S3 + CloudFront | Static React build; 3s edge cache on dashboard endpoint |
| Backend API | ECS Express Mode (Fargate) | FastAPI container from ECR; ALB + auto-scaling auto-provisioned |
| Redis | EC2 t4g.nano (ARM) | Docker, `redis:7-alpine`, password-protected, private SG, same VPC as Fargate tasks |
| Database | Supabase | External, free tier viable for MVP |
| Auth (admin) | Supabase Auth | External |
| Backup storage | S3 | Hourly + automatic pre-action `pg_dump` snapshots |
| DNS | Route 53 | A-record alias to ALB for custom domain |
| TLS | ACM (CloudFront, ALB) | Auto-managed (CloudFront), manual cert + listener attach (ALB) |
| Container registry | ECR | For ECS Fargate image pulls |
| Logs | CloudWatch | Auto-configured by Express Mode |

## Cost estimate

| Item | Monthly |
|---|---|
| ECS Express Mode — 1 Fargate task (0.5 vCPU / 1GB), running 24/7 | ~$10–13 |
| ALB (provisioned by Express Mode) | ~$5–8 |
| EC2 t4g.nano (Redis) | ~$3–4 |
| EBS for Redis (8GB gp3) | ~$1 |
| S3 (frontend + backups) | ~$1–3 |
| CloudFront | ~$1 |
| Route 53 | ~$0.50 |
| Supabase | $0 (free tier) |
| **Total** | **~$22–32** |

**Cost note**: The ALB is ~$5–8/mo at low traffic but can grow with LCU usage if SSE connections multiply. At 100+ concurrent SSE connections the ALB cost could push to $10–15/mo, still in budget. If you start running multiple unrelated services on AWS, ECS Express Mode automatically consolidates up to 25 services behind a single ALB, amortizing this cost.

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
- ECS Express Mode auto-creates CloudWatch alarms on Fargate task health.

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
2. `docker build` (linux/x86_64 — Express Mode default architecture).
3. `docker push` to ECR.
4. `aws ecs update-express-gateway-service --service-arn <arn> --primary-container '{"image":"<new-image-uri>"}'`.

ECS Express Mode handles the rolling deploy with health checks. No SSH, no manual restart.

> Note: Express Mode does not currently support blue-green deployments. Rolling deploys only. For MVP that's fine; revisit if zero-downtime guarantees become more critical.

### Redis EC2
- Provisioned via Terraform/CloudFormation (one-time).
- No CI/CD; updates done manually via SSH only when explicitly needed.

## Environment configuration

| Variable | Where | Notes |
|---|---|---|
| `DATABASE_URL` | Fargate task env | Supabase connection string |
| `REDIS_URL` | Fargate task env | `redis://:password@<redis-ec2-private-ip>:6379` |
| `REDIS_PASSWORD` | EC2 + Fargate task env | Shared secret |
| `SUPABASE_JWKS_URL` | Fargate task env | For verifying admin JWTs |
| `JUDGE_JWT_SECRET` | Fargate task env | HS256 secret for judge tokens |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` | Fargate task env | Web push |
| `ADMIN_EMAIL_ALLOWLIST` | Fargate task env | Comma-separated list |
| `BACKUP_S3_BUCKET` | Fargate task env | Where `pg_dump` exports go |
| `AWS_REGION` | Fargate task env | For S3 + CloudWatch SDK calls |
| `VITE_API_URL` | GitHub Actions secret | Baked into frontend build |
| `VITE_VAPID_PUBLIC_KEY` | GitHub Actions secret | Baked into frontend build |

Environment variables are set on the task definition (configurable via Express Mode's "Additional configurations" section in the console, or directly on the task definition revision).

## VPC networking note

ECS Express Mode runs Fargate tasks in your VPC by default. The Redis EC2 sits in the same VPC, simplifying connectivity:

1. Create a VPC (or use default) with at least 2 subnets across AZs (Express Mode requires multi-AZ for the ALB).
2. Launch the t4g.nano EC2 in a private subnet.
3. Security group `redis-sg`: inbound TCP 6379 from `fargate-task-sg` only.
4. ECS Express Mode auto-creates a security group for the Fargate tasks; modify it to allow outbound TCP 6379 to `redis-sg`.
5. Verify the Fargate task can reach Redis by checking `/health/redis` returns 200.

Document this in IaC. The security group cross-reference is the most easily forgotten setup step.

## IAM roles needed

ECS Express Mode requires two IAM roles:

1. **Task execution role** (`ecsTaskExecutionRole`) — lets Fargate pull the image from ECR and write logs to CloudWatch. Use the AWS-managed `AmazonECSTaskExecutionRolePolicy`.
2. **Infrastructure role** (`ecsInfrastructureRoleForExpressServices`) — lets Express Mode provision the ALB, target groups, security groups, etc. Use the AWS-managed `AmazonECSInfrastructureRoleforExpressGatewayServices`.
3. **Task role** (optional, additional) — for app code to access AWS services. Ours needs S3 (backups) and CloudWatch (custom metrics) access.

## Pre-tournament checklist

Run morning of every tournament. Full version in [`operations.md`](operations.md#pre-tournament-checklist).

1. ✅ ECS Express Mode service status: `ACTIVE` (check via `aws ecs describe-express-gateway-service`).
2. ✅ Redis EC2 is `running` with `2/2 status checks passed`.
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
| Fargate task crashes | ECS Express Mode auto-replaces; ALB health checks redirect traffic to healthy task |
| Bad deploy | Rolling deploy with health checks; failed task is replaced and old version remains serving |
| ALB issues | Rare; managed by AWS. Status visible in EC2 console |
| Redis EC2 dies | CloudWatch alarm fires; auto-recovery migrates to new hardware (~2-5 min). Public falls back to polling. SSE clients reconnect. See runbook in `operations.md` |
| Redis container crashes | `restart: always` brings it back in seconds |
| Supabase down | Application down. No mitigation; rely on Supabase SLA. Print backup is the only recourse |
| Network at venue dies | All clients show disconnected overlay. Print backup; admin can submit results retroactively when network returns |
| Bad admin edit corrupts data | Restore from most recent backup snapshot (manual or hourly) |

## Future infrastructure work

- Move Postgres from Supabase to RDS if Supabase costs grow.
- Consider ElastiCache if Redis on EC2 becomes a recurring pain point.
- Multi-region failover (probably never needed).
- Add proper observability (Sentry, custom metrics) — currently CloudWatch logs only.
- Migrate to direct ECS API if we need blue-green deploys, sidecars, or custom auto-scaling metrics. Express Mode + standard ECS coexist; no service migration needed.
