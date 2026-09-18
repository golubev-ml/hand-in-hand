#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/deploy"

# Usage: ./deploy/deploy.sh test|prod. The tracked profile contains only public
# environment-specific values; deploy/.env and deploy/secrets remain local.
DEPLOY_ENV="${1:-${DEPLOY_ENV:-test}}"
case "$DEPLOY_ENV" in
  test|prod) ;;
  *) echo "Usage: $0 test|prod" >&2; exit 2 ;;
esac

set -a
if [ -f .env ]; then
  . ./.env
fi
if [ -f "./secrets/$DEPLOY_ENV.env" ]; then
  . "./secrets/$DEPLOY_ENV.env"
fi
for secret_env in ./secrets/"$DEPLOY_ENV"/*.env; do
  [ -e "$secret_env" ] && . "$secret_env"
done
# Public profile is authoritative for domains, gateway contour and production metric.
# Variables omitted by it (including the current test metric) keep their local value.
. "./env/$DEPLOY_ENV.env"
set +a

TRAEFIK_NETWORK="${TRAEFIK_NETWORK:-deploy_web}"
if [ "${USE_EXTERNAL_TRAEFIK:-false}" = "true" ]; then
  docker network inspect "$TRAEFIK_NETWORK" >/dev/null
  PROXY_ARGS=()
  PROXY_SERVICES=()
else
  docker network inspect "$TRAEFIK_NETWORK" >/dev/null 2>&1 || docker network create "$TRAEFIK_NETWORK" >/dev/null
  PROXY_ARGS=(--profile bundled-proxy)
  PROXY_SERVICES=(traefik)
fi

echo "[1/5] Starting database..."
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

echo "[2/5] Building images for $DEPLOY_ENV (docker cache)..."
docker compose build api frontend landing

echo "[3/5] Running migrations..."
docker compose run --rm api sh -c 'cd /app && alembic upgrade head'

echo "[4/5] Starting api, frontend, landing, traefik..."
docker compose "${PROXY_ARGS[@]}" up -d api frontend landing "${PROXY_SERVICES[@]}"

echo "[5/5] Waiting for Let's Encrypt + HTTPS..."
DOMAIN="${DOMAIN:-hand-in-hand-kzn.ru}"
LANDING_DOMAIN="${LANDING_DOMAIN:-hand.hand-in-hand-kzn.ru}"

wait_https() {
  local url="$1"
  for i in {1..30}; do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "HTTPS OK: $url"
      return 0
    fi
    sleep 5
  done
  echo "HTTPS не поднялся: $url" >&2
  return 1
}

wait_https "https://$DOMAIN/api/health"
wait_https "https://$DOMAIN/" || echo ">> основной сайт ещё не отвечает: проверьте DNS и логи traefik" >&2
wait_https "https://$LANDING_DOMAIN/landing" || echo ">> лендинг ещё не отвечает: проверьте DNS и логи traefik" >&2

echo ""
echo "Deployment completed."
echo "Site:     https://$DOMAIN"
echo "Admin:    https://$DOMAIN/admin"
echo "Settings: https://$DOMAIN/admin/settings"
echo "Landing:  https://$LANDING_DOMAIN/landing"
echo "Docs:     https://$DOMAIN/docs"
if [ "${APP_ENV:-local}" != "prod" ]; then
  echo "MailHog: http://localhost:9000"
fi
