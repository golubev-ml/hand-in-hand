# Бэкенд («Краски детства»)

FastAPI + SQLAlchemy + Alembic. REST API для сайта и админ-панель.

## Структура

| Файл / папка | Назначение |
|---|---|
| `main.py` | создание приложения: роутеры, `/uploads`, логирование запросов, раздача сборки фронта, `/api/health` |
| `database.py` | подключение БД: `DATABASE_URL` из окружения (Postgres), без него — SQLite `back/database.db` |
| `models.py` | таблицы: `managers`, `pictures`, `donations`, `logs` |
| `schemas.py` | Pydantic-схемы валидации запросов/ответов |
| `auth.py` | bcrypt-хеши паролей, JWT-токены, проверка текущего пользователя |
| `admin_panel.py` | админка `/admin`: статистика, загрузка картинок, пожертвования, лог |
| `routers/` | API-роутеры: `auth_router`, `pictures`, `donations`, `logs` |
| `alembic/`, `alembic.ini` | миграции БД (файлы миграций — в `alembic/versions/`) |
| `uploads/` | загруженные картинки, доступны по `/uploads/<файл>` |
| `requirements.txt` | зависимости Python |
| `Dockerfile` | образ бэкенда для Docker |

## Локальный запуск

```bash
cd back
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

alembic upgrade head            # создать/обновить таблицы
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Адреса после запуска:
- Swagger (документация API): http://localhost:8000/docs
- Админка: http://localhost:8000/admin
  - `admin / admin123` (создаётся при первом запуске)
  - `hand_admin / 0h8Zkqv3wG29`
  - это тестовые доступы, в продакшене пароли менять!

## База данных

- Без переменных окружения — SQLite, файл `back/database.db`.
- С `DATABASE_URL` (например `postgresql://postgres:postgres@db:5432/hand_in_hand`) — Postgres; так работает в Docker.
- Изменения схемы — только миграциями:

```bash
alembic revision --autogenerate -m "описание изменения"
alembic upgrade head
```

## Основные эндпоинты API

| Метод | Адрес | Описание | Доступ |
|---|---|---|---|
| POST | `/api/auth/login` | вход, выдаёт JWT | все |
| GET | `/api/pictures` | список рисунков | все |
| POST | `/api/pictures/upload` | загрузка картинки | админ |
| PATCH | `/api/pictures/{id}` | изменение рисунка | админ |
| POST | `/api/donations` | создать пожертвование | все |
| GET | `/api/donations` | список пожертвований | админ |
| PATCH | `/api/donations/{id}/status` | смена статуса пожертвования | админ |
| GET | `/api/logs` | лог запросов | админ |
| GET | `/api/health` | проверка здоровья сервиса | все |

Полный актуальный список — в Swagger: `/docs`.

## Запуск в Docker (весь стек)

Из корня репозитория:

```bash
bash deploy/deploy.sh   # Postgres → миграции → фронтенд → API
bash deploy/stop.sh     # остановка
```

Порты: API — 8000, фронтенд — 3000, Postgres — 5432.