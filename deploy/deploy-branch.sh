#!/bin/bash
set -euo pipefail

# ─── deploy-branch.sh: выкатка и регресс ветки ───────────────────────────────────
# Использование:
#   deploy-branch.sh [ветка] [флаги]
# 
# Ветка: по умолчанию order
# Флаги:
#   --wipe-db        - удалить БД и том
#   --rebuild-api    - пересобрать API (по умолчанию включен)
#   --rebuild-front  - пересобрать фронт (по умолчанию выключен)
#
# Примеры:
#   ./deploy-branch.sh                           # выкатить order, пересобрать API
#   ./deploy-branch.sh main --wipe-db             # выкатить main, пересобрать API, удалить БД
#   ./deploy-branch.sh order --rebuild-front      # выкатить order, пересобрать фронт и API

BRANCH="${1:-order}"
WIPE_DB=false
REBUILD_API=true
REBUILD_FRONT=false

# Парсим флаги
for arg in "$@"; do
  case "$arg" in
    --wipe-db) WIPE_DB=true ;;
    --rebuild-api) REBUILD_API=true ;;
    --no-rebuild-api) REBUILD_API=false ;;
    --rebuild-front) REBUILD_FRONT=true ;;
  esac
done

REPO_DIR="${REPO_DIR:-$HOME/my-deploy}"
SECRETS_FILE="/root/.hand-env"
DEPLOY_ENV="$REPO_DIR/deploy/.env"
DOCKER_COMPOSE="docker-compose"

# Проверяем docker-compose v2
if ! command -v "$DOCKER_COMPOSE" &>/dev/null; then
  DOCKER_COMPOSE="docker compose"
fi

# ─── Подготовка секретов ──────────────────────────────────────────────────────
echo ">>> Подготовка окружения..."

# Если секреты нет, создаём из текущего .env в репо
if [[ ! -f "$SECRETS_FILE" ]]; then
  echo ">>> Создание $SECRETS_FILE из deploy/.env..."
  if [[ ! -f "$DEPLOY_ENV" ]]; then
    echo "⚠️  Не найден deploy/.env, создаём минимальный..."
    cat > "$DEPLOY_ENV" <<'EOF'
APP_ENV=local
SECRET_KEY=dev-only-insecure-key
ADMIN_LOGIN=hand_admin
ADMIN_PASSWORD=changeme123
SMTP_HOST=mailhog
SMTP_PORT=1025
MAIL_FROM=noreply@kraski-detstva.ru
BASE_URL=http://localhost
CORS_ORIGINS=http://localhost
EOF
  fi
  cp "$DEPLOY_ENV" "$SECRETS_FILE"
  echo "✓ Секреты созданы в $SECRETS_FILE"
fi

# Копируем секреты в deploy/.env
cp "$SECRETS_FILE" "$DEPLOY_ENV"
echo "✓ Секреты скопированы в $DEPLOY_ENV"

# ─── Git операции ─────────────────────────────────────────────────────────────
echo ">>> Git операции..."

if [[ ! -d "$REPO_DIR" ]]; then
  echo "⚠️  Репозиторий не найден в $REPO_DIR"
  exit 1
fi

cd "$REPO_DIR"

git fetch origin
echo "✓ git fetch origin"

git checkout -B "$BRANCH" "origin/$BRANCH"
echo "✓ git checkout -B $BRANCH origin/$BRANCH"

git reset --hard "origin/$BRANCH"
echo "✓ git reset --hard origin/$BRANCH"

git clean -fd -e .env
echo "✓ git clean -fd -e .env"

# ─── Подготовка Docker ────────────────────────────────────────────────────────
echo ">>> Подготовка Docker..."

cd "$REPO_DIR/deploy"

if [[ "$WIPE_DB" == true ]]; then
  echo ">>> Удаление БД (флаг --wipe-db)..."
  $DOCKER_COMPOSE down || true
  echo "✓ docker-compose down"
  
  # Удаляем том БД
  VOLUME_NAME=$(basename "$REPO_DIR")_db_1
  docker volume rm "$VOLUME_NAME" 2>/dev/null || echo "⚠️  Том $VOLUME_NAME не найден или уже удален"
  echo "✓ Том БД удален"
else
  echo ">>> Остановка только изменяемых сервисов..."
  # Останавливаем только API и фронт, БД остаётся
  $DOCKER_COMPOSE stop api frontend 2>/dev/null || true
  echo "✓ docker-compose stop api frontend"
fi

# ─── Сборка по флагам ─────────────────────────────────────────────────────────
echo ">>> Сборка сервисов..."

if [[ "$REBUILD_API" == true ]]; then
  echo ">>> Пересборка API (флаг --rebuild-api)..."
  $DOCKER_COMPOSE build --no-cache api
  echo "✓ docker-compose build api"
fi

if [[ "$REBUILD_FRONT" == true ]]; then
  echo ">>> Пересборка фронта (флаг --rebuild-front)..."
  $DOCKER_COMPOSE build --no-cache frontend
  echo "✓ docker-compose build frontend"
fi

# ─── Поднимаем сервисы ────────────────────────────────────────────────────────
echo ">>> Запуск сервисов..."

$DOCKER_COMPOSE up -d
echo "✓ docker-compose up -d"

# ─── Миграции ─────────────────────────────────────────────────────────────────
echo ">>> Запуск миграций..."

sleep 2  # даём БД время поднять

$DOCKER_COMPOSE run --rm api alembic upgrade head
echo "✓ alembic upgrade head"

# ─── Регресс-тесты ────────────────────────────────────────────────────────────
echo ""
echo ">>> Регресс-тесты..."

FAILED=0

# Фронт поднялся
echo -n "  Фронт: "
if curl -sf http://localhost/ >/dev/null 2>&1; then
  echo "✓ OK"
else
  echo "✗ FAIL"
  FAILED=$((FAILED + 1))
fi

# API поднялся
echo -n "  API: "
if curl -sf http://localhost/api/pictures >/dev/null 2>&1; then
  echo "✓ OK"
else
  echo "✗ FAIL"
  FAILED=$((FAILED + 1))
fi

# Миграции
echo -n "  Миграции: "
if $DOCKER_COMPOSE run --rm api alembic current >/dev/null 2>&1; then
  echo "✓ OK"
else
  echo "✗ FAIL"
  FAILED=$((FAILED + 1))
fi

# Админка: логин
echo -n "  Админка логин: "
ADMIN_LOGIN=$(grep "ADMIN_LOGIN" "$DEPLOY_ENV" | cut -d= -f2)
ADMIN_PASSWORD=$(grep "ADMIN_PASSWORD" "$DEPLOY_ENV" | cut -d= -f2)
COOKIE_JAR=$(mktemp)
if curl -sf -c "$COOKIE_JAR" -d "login=$ADMIN_LOGIN&password=$ADMIN_PASSWORD" \
    http://localhost/admin/login -w "%{http_code}" 2>/dev/null | grep -q "302\|200"; then
  echo "✓ OK"
else
  echo "✗ FAIL"
  FAILED=$((FAILED + 1))
fi
rm -f "$COOKIE_JAR"

# Добавить картинку
echo -n "  Загрузка картинки: "
TEMP_IMG=$(mktemp --suffix=.jpg)
dd if=/dev/zero bs=1024 count=10 of="$TEMP_IMG" 2>/dev/null
ADMIN_LOGIN=$(grep "ADMIN_LOGIN" "$DEPLOY_ENV" | cut -d= -f2)
ADMIN_PASSWORD=$(grep "ADMIN_PASSWORD" "$DEPLOY_ENV" | cut -d= -f2)
COOKIE_JAR=$(mktemp)
# Логинимся
curl -sf -c "$COOKIE_JAR" -d "login=$ADMIN_LOGIN&password=$ADMIN_PASSWORD" \
    http://localhost/admin/login >/dev/null 2>&1 || true
# Загружаем
UPLOAD_RESPONSE=$(curl -sf -b "$COOKIE_JAR" -F "file=@$TEMP_IMG" \
    -F "title=Test" -F "author=Test Author" -F "age=10" -F "price=1000" \
    -w "%{http_code}" http://localhost/admin/pictures/upload 2>/dev/null || echo "500")
if echo "$UPLOAD_RESPONSE" | grep -q "302\|200"; then
  # Проверяем что картинка видна в API
  if curl -sf http://localhost/api/pictures | grep -q '"id"'; then
    echo "✓ OK"
  else
    echo "✗ FAIL"
    FAILED=$((FAILED + 1))
  fi
else
  echo "✗ FAIL"
  FAILED=$((FAILED + 1))
fi
rm -f "$TEMP_IMG" "$COOKIE_JAR"

# Заказ: телефон 78889990001 -> paid
echo -n "  Заказ (paid): "
ORDER_RESPONSE=$(curl -sf -X POST http://localhost/api/orders \
    -H "Content-Type: application/json" \
    -d '{
      "customer_name":"Test",
      "customer_email":"test@example.com",
      "customer_phone":"78889990001",
      "picture_ids":[1]
    }' 2>/dev/null)
if echo "$ORDER_RESPONSE" | grep -q '"payment_status":"paid"'; then
  echo "✓ OK"
else
  echo "✗ FAIL (response: $ORDER_RESPONSE)"
  FAILED=$((FAILED + 1))
fi

# Заказ: телефон 78889990002 -> failed
echo -n "  Заказ (failed): "
ORDER_RESPONSE=$(curl -sf -X POST http://localhost/api/orders \
    -H "Content-Type: application/json" \
    -d '{
      "customer_name":"Test2",
      "customer_email":"test2@example.com",
      "customer_phone":"78889990002",
      "picture_ids":[2]
    }' 2>/dev/null)
if echo "$ORDER_RESPONSE" | grep -q '"payment_status":"failed"'; then
  echo "✓ OK"
else
  echo "✗ FAIL (response: $ORDER_RESPONSE)"
  FAILED=$((FAILED + 1))
fi

# Заказ видна в админке
echo -n "  Заказ в админке: "
ADMIN_LOGIN=$(grep "ADMIN_LOGIN" "$DEPLOY_ENV" | cut -d= -f2)
ADMIN_PASSWORD=$(grep "ADMIN_PASSWORD" "$DEPLOY_ENV" | cut -d= -f2)
COOKIE_JAR=$(mktemp)
curl -sf -c "$COOKIE_JAR" -d "login=$ADMIN_LOGIN&password=$ADMIN_PASSWORD" \
    http://localhost/admin/login >/dev/null 2>&1 || true
if curl -sf -b "$COOKIE_JAR" http://localhost/admin/orders | grep -q "Test"; then
  echo "✓ OK"
else
  echo "✗ FAIL"
  FAILED=$((FAILED + 1))
fi
rm -f "$COOKIE_JAR"

# MailHog: письмо "спасибо за вашу покупку"
echo -n "  Email в MailHog: "
if curl -sf http://localhost:9000/api/v2/messages | grep -q "спасибо за вашу покупку"; then
  echo "✓ OK"
else
  echo "✗ FAIL"
  FAILED=$((FAILED + 1))
fi

echo ""
if [[ $FAILED -eq 0 ]]; then
  echo "✓ Все регресс-тесты пройдены!"
  exit 0
else
  echo "✗ Некоторые регресс-тесты не пройдены ($FAILED ошибок)"
  exit 1
fi
