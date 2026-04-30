#!/bin/bash
set -euo pipefail

# Install Docker + Compose plugin
dnf update -y
dnf install -y docker
systemctl enable docker
systemctl start docker
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Write redis env
mkdir -p /opt/redis
cat > /opt/redis/.env <<EOF
REDIS_PASSWORD=${redis_password}
EOF
chmod 600 /opt/redis/.env

# Write docker-compose.yml
cat > /opt/redis/docker-compose.yml <<'COMPOSE'
services:
  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 100mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "$$REDIS_PASSWORD", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  redis-data:
COMPOSE

# Systemd unit to start Compose on boot
cat > /etc/systemd/system/redis-compose.service <<'UNIT'
[Unit]
Description=Redis (Docker Compose)
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/redis
EnvironmentFile=/opt/redis/.env
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=60

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable redis-compose
systemctl start redis-compose
