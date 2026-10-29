# hand-in-hand

Благотворительная онлайн-галерея творческих работ детей, проходящих лечение от онкологических заболеваний.

## Требования

- Node.js **22** (см. `front/.mise.toml`)
- npm
- Docker и Docker Compose
- Docker API **1.44+** (для production-деплоя через Traefik)
- Python 3.11+ и `pip` — для локального запуска бэкенда без Docker

## Установка зависимостей

```bash
cd front
npm ci
```

## Локальный запуск

### Фронтенд (галерея)

```bash
cd front
npm run dev
```

Сервер Vite запускается на `http://localhost:5173`.
Проксирует `/api` и `/uploads` на `http://localhost:8000`.

### Бэкенд и база (Docker)

```bash
./deploy/deploy.sh test
```

Скрипт поднимает Postgres, API, фронтенд, лендинг, Traefik и MailHog,
применяет миграции и ждёт HTTPS.

Для остановки:

```bash
./deploy/stop.sh
```

## Проверки и тесты

### Фронтенд

```bash
cd front
npm run typecheck   # TypeScript без генерации файлов
npm run check       # typecheck + build
npm run build       # production-сборка
```

Docker-сборка фронтенда сначала запускает `typecheck`, потом `build`
(см. `deploy/Dockerfile.frontend`).

### Бэкенд

```bash
python -m pytest test/unit -q
python -m pytest test/api -q
python -m pytest test/e2e -q --ignore-https-errors
```

Или внутри контейнера через `test/test.sh`.

## Миграции

Применить миграции Alembic:

```bash
./migrate.sh
```

Эквивалентно `cd back && alembic upgrade head`.

## Запуск test/prod

```bash
./deploy/deploy.sh test
./deploy/deploy.sh prod
```

Перед запуском профиль читает публичные параметры из
`deploy/env/<окружение>.env`, затем локальные `deploy/.env` и секреты из
`deploy/secrets/<окружение>.env`/`*.env`. Секреты не коммитятся в Git.

| Окружение | Основной сайт | Лендинг |
|---|---|---|
| test | `hand-in-hand-kzn.ru` — витрина `/`, API `/api`, админка `/admin`, возвраты `/payment` | `hand.hand-in-hand-kzn.ru/landing` |
| prod | `iskusstvo-chtoby-zhit.ru` — витрина `/`, API `/api`, админка `/admin`, возвраты `/payment` | `hand.iskusstvo-chtoby-zhit.ru/landing` |

## Настройка платёжного шлюза

Используется тестовый контур Сбербанка:
`https://ecomtest.sberbank.ru/ecomm/gateway/api/rest/`.

Чтобы включить реальные платежи:

1. Перейти в `/admin/settings`.
2. Включить «Оплата включена».
3. Заполнить:
   - `userName` и пароль шлюза;
   - `merchantLogin`, терминал и `keyId` — если требуются контуром.

По умолчанию оплата **выключена**: чекаут работает как заглушка.

## Бэкапы и восстановление

Постоянные данные живут в Docker- volumes:

- `postgres_data` — база Postgres;
- `uploads_data` — загруженные изображения;
- `backups_data` — резервные копии.

Для бэкапа перед production-деплоем:

```bash
docker compose exec db pg_dump -U postgres hand_in_hand > backup.sql
docker cp hand-in-hand-api:/app/uploads ./uploads-backup
```

## Диагностика деплоя

После изменений proxy:

1. Проверить Docker API сервера: `docker version`.
2. Убедиться, что `deploy/docker-compose.yml` использует
   `DOCKER_API_VERSION: "1.44"`.
3. Проверить маршруты:
   - `/`
   - `/api/health`
   - `/admin`
   - `/landing` (лендинг)
4. Посмотреть логи Traefik: отсутствие ошибок Docker API.

## Обязательные секреты

- `ADMIN_LOGIN`
- `ADMIN_PASSWORD`
- `SBER_USER_NAME`
- `SBER_PASSWORD`
- `SBER_KEY`
- `ACME_EMAIL`
- `YANDEX_METRIKA_ID` / `METRIKA_ID`

Значения не должны попадать в репозиторий и логи.

## Production checklist

- [ ] `npm run typecheck` и `npm run build` проходят локально.
- [ ] Docker-сборка фронтенда не падает на `typecheck`.
- [ ] Миграции применены (`./migrate.sh`).
- [ ] `APP_ENV=prod` задан в окружении.
- [ ] Секреты вынесены в `deploy/secrets/prod.env` или env-сервера.
- [ ] Проверены `/`, `/api/health`, `/admin` и `/landing` по HTTPS.
- [ ] Traefik запущен без ошибок Docker API.
- [ ] Создана резервная копия БД и загруженных изображений.
