#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/deploy"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

# HIH-9: лендинг на поддомене раздаёт статику из LANDING_DIR (по умолчанию /root/landing)
LANDING_DIR="${LANDING_DIR:-/root/landing}"
mkdir -p "$LANDING_DIR"
if [ ! -f "$LANDING_DIR/index.html" ]; then
  echo ">> В $LANDING_DIR нет index.html — кладём placeholder из репозитория"
  cp "$ROOT_DIR/landing/index.html" "$LANDING_DIR/index.html"
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

echo "[2/5] Building images (docker cache)..."
docker compose build api frontend

echo "[3/5] Running migrations..."
docker compose run --rm api sh -c 'cd /app && alembic upgrade head'

echo "[4/5] Starting api, frontend, landing, traefik..."
docker compose up -d api frontend landing traefik

echo "[5/5] Waiting for Let's Encrypt + HTTPS..."
DOMAIN="${DOMAIN:-hand-in-hand.ru}"
LANDING_DOMAIN="${LANDING_DOMAIN:-hand.hand-in-hand.ru}"
LEGACY_DOMAIN="${LEGACY_DOMAIN:-hand-in-hand-kzn.ru}"

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
# Первый выпуск сертификатов для трёх хостов может занять время — предупреждаем, но не роняем деплой
wait_https "https://$DOMAIN/" || echo ">> основной сайт ещё не отвечает: проверьте DNS и логи traefik" >&2
wait_https "https://$LANDING_DOMAIN/" || echo ">> лендинг ещё не отвечает: проверьте DNS для $LANDING_DIR" >&2
curl -sf "https://$LEGACY_DOMAIN/api/health" >/dev/null 2>&1 \
  && echo "HTTPS OK: переходный домен $LEGACY_DOMAIN работает" \
  || echo ">> переходный домен $LEGACY_DOMAIN пока не отвечает" >&2

echo ""
echo "Deployment completed."
echo "Site:     https://$DOMAIN"
echo "Admin:    https://$DOMAIN/admin"
echo "Settings: https://$DOMAIN/admin/settings"
echo "Landing:  https://$LANDING_DOMAIN  (файлы: $LANDING_DIR)"
echo "Docs:     https://$DOMAIN/docs"
if [ "${APP_ENV:-local}" != "prod" ]; then
  echo "MailHog: http://localhost:9000"
fi
