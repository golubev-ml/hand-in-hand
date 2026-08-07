# Предложение по развертыванию

Оптимальное решение — единый Docker Compose-стек с базовой конфигурацией и тремя окружениями: `local`, `test`, `prod`.

## Целевая схема

```text
Internet
   │ 80/443
 Traefik ─── TLS / Let's Encrypt
   ├── /api, /admin, /uploads → FastAPI
   └── остальные запросы      → Frontend (Nginx)
                                   │
FastAPI ─────────────────────── PostgreSQL
```

Наружу публикуются только порты Traefik `80/443`. API, frontend и PostgreSQL остаются во внутренней Docker-сети. Фронтенд уже использует относительные `/api` и `/uploads`, поэтому менять адрес API в React не потребуется.

## Предлагаемая структура

```text
deploy/
├── compose.yml
├── compose.local.yml
├── compose.test.yml
├── compose.prod.yml
├── Dockerfile.api
├── Dockerfile.frontend
├── nginx.conf
├── deploy.sh
├── env/
│   ├── local.env
│   ├── test.env
│   └── prod.env
└── secrets/
    ├── local/
    ├── test/
    └── prod/
```

Запуск:

```bash
./deploy/deploy.sh local
./deploy/deploy.sh test
./deploy/deploy.sh prod
```

Базовый `compose.yml` содержит общие сервисы. Окружения переопределяют домены, TLS, опубликованные порты, режим разработки и политики перезапуска.

## Сертификаты

Для test/prod Traefik получает сертификаты через Let's Encrypt:

- `test.example.ru` — тестовый стек;
- `example.ru` — production;
- автоматическое продление;
- HTTP автоматически перенаправляется на HTTPS;
- хранилища `acme.json` у test и prod должны быть разными.

Для local можно оставить HTTP или подключить локальный сертификат `mkcert`.

## Секреты

Из Compose и репозитория нужно убрать:

- пароль PostgreSQL;
- JWT `SECRET_KEY`;
- логин и пароль начального администратора.

Использовать раздельные Docker secrets:

```text
secrets/test/db_password
secrets/test/jwt_secret
secrets/test/admin_password

secrets/prod/db_password
secrets/prod/jwt_secret
secrets/prod/admin_password
```

Каталог `secrets/` должен быть в `.gitignore`, а на сервере — иметь ограниченные права. Несекретные параметры вроде домена, имени базы и ACME email можно хранить в `env/*.env`.

## Что сейчас нужно исправить обязательно

- API фактически билдится дважды: ручная проверка хеша теряет смысл из-за последующего `docker compose up --build`. Лучше доверить определение изменений Docker build cache.
- Frontend каждый запуск выполняет `npm install` и пишет `dist` в исходники. Нужен multi-stage image: `npm ci` → `npm run build` → Nginx.
- PostgreSQL сейчас доступен на хосте через `5432`; на test/prod порт публиковать нельзя.
- Загруженные изображения находятся внутри API-контейнера и пропадут при пересоздании. Для `/app/uploads` нужен постоянный volume.
- В коде зашиты пароли администратора, включая `admin/admin123`. В test/prod приложение должно завершаться с ошибкой, если секреты не заданы.
- Публичный `/api/auth/register` позволяет кому угодно создать менеджера. Его нужно отключить либо защитить правами администратора.
- `CORS allow_origins=["*"]` необходимо заменить доменами окружения или убрать при работе через единый origin.
- Для admin cookie следует включить `secure`, `samesite` и подходящий срок жизни.
- Для БД и uploads необходимо настроить резервное копирование.

## Деплой

Новый скрипт должен:

1. Проверить выбранное окружение и наличие секретов.
2. Собрать изменившиеся образы через Docker cache.
3. Поднять PostgreSQL и дождаться healthcheck.
4. Выполнить `alembic upgrade head` отдельным одноразовым контейнером.
5. Поднять API, frontend и Traefik.
6. Проверить `/api/health`.
7. Не пересоздавать volume базы и uploads без явной команды.

Для реализации понадобятся домены test/prod и email для Let's Encrypt.
