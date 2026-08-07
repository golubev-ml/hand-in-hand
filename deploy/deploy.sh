#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"
BACK_DIR="$ROOT_DIR/back"
FRONT_DIR="$ROOT_DIR/front"

cd "$DEPLOY_DIR"

echo "[1/4] Starting database..."
docker compose up -d db

for i in {1..30}; do
  if docker compose ps db | grep -q 'healthy'; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "Database did not become healthy in time." >&2
    exit 1
  fi
  sleep 2
done

echo "[2/4] Running migrations..."
docker compose run --rm api sh -c 'cd /app && alembic upgrade head'

echo "[3/4] Rebuilding and starting frontend..."
docker compose up -d --force-recreate frontend

echo "[4/4] Restarting API..."
docker compose up -d --build --force-recreate api

echo "Deployment completed."
echo "Frontend: http://localhost:3000"
echo "API: http://localhost:8000"
echo "Docs: http://localhost:8000/docs"
