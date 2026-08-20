#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/deploy"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

echo "[1/4] Starting database..."
docker compose up -d db
if [ "${APP_ENV:-local}" != "prod" ]; then
  echo "Starting MailHog for ${APP_ENV:-local} environment..."
  docker compose up -d mailhog
fi
for i in {1..30}; do
  docker compose ps db | grep -q 'healthy' && break
  [ "$i" -eq 30 ] && { echo "DB not healthy" >&2; exit 1; }
  sleep 2
done

echo "[2/4] Building images (docker cache)..."
docker compose build api frontend

echo "[3/4] Running migrations..."
docker compose run --rm api sh -c 'cd /app && alembic upgrade head'

echo "[4/4] Starting api, frontend, traefik..."
docker compose up -d api frontend traefik

echo "Waiting for Let's Encrypt + HTTPS..."
https_ready=false
for i in {1..30}; do
  if curl -sf https://hand-in-hand-kzn.ru/api/health >/dev/null 2>&1; then
    echo "HTTPS OK"
    https_ready=true
    break
  fi
  sleep 5
done
if [ "$https_ready" != true ]; then
  echo "HTTPS did not become ready in time." >&2
  exit 1
fi

echo ""
echo "Deployment completed."
echo "Site:  https://hand-in-hand-kzn.ru"
echo "Admin: https://hand-in-hand-kzn.ru/admin"
echo "Docs:  https://hand-in-hand-kzn.ru/docs"
if [ "${APP_ENV:-local}" != "prod" ]; then
  echo "MailHog: http://localhost:9000"
fi
