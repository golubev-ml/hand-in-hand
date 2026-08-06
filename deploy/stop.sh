#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"

cd "$DEPLOY_DIR"

echo "Stopping containers..."
docker compose stop api db >/dev/null 2>&1 || true

echo "Removing API container while preserving database volume..."
docker compose rm -f api >/dev/null 2>&1 || true

echo "Database volume is preserved."
