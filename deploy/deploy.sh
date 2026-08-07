#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"
BACK_DIR="$ROOT_DIR/back"
FRONT_DIR="$ROOT_DIR/front"

cd "$DEPLOY_DIR"

echo "[1/5] Starting database and mailhog..."
docker compose up -d db mailhog

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

compute_api_hash() {
  find "$BACK_DIR" -type f \( -name '*.py' -o -name 'requirements.txt' \) -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    | sha256sum \
    | awk '{print $1}'
}

API_HASH_FILE="$DEPLOY_DIR/.api_build_hash"
CURRENT_API_HASH=$(compute_api_hash)
PREVIOUS_API_HASH=""
if [ -f "$API_HASH_FILE" ]; then
  PREVIOUS_API_HASH=$(cat "$API_HASH_FILE")
fi

if [ "$CURRENT_API_HASH" != "$PREVIOUS_API_HASH" ]; then
  echo "[2/5] API code changed; rebuilding API image..."
  docker compose build api
  echo "$CURRENT_API_HASH" > "$API_HASH_FILE"
else
  echo "[2/5] API code unchanged; using existing API image."
fi

echo "[3/5] Running migrations..."
docker compose run --rm api sh -c 'cd /app && alembic upgrade head'

echo "[4/5] Rebuilding and starting frontend..."
docker compose up -d --force-recreate frontend

echo "[5/5] Restarting API..."
docker compose up -d --build --force-recreate api

echo ""
echo "Deployment completed."
echo "Frontend: http://localhost:3000"
echo "API:      http://localhost:8000"
echo "Admin:    http://localhost:8000/admin"
echo "Docs:     http://localhost:8000/docs"
echo "MailHog (письма): http://localhost:9000"
