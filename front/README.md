# Фронтенд («Краски детства»)

React + TypeScript + Vite + Tailwind. Сайт благотворительного фонда.

## Структура

| Файл / папка | Назначение |
|---|---|
| `src/App.tsx` | весь сайт: шапка, hero, галерея, корзина, оформление заказа, пожертвования, контакты, подвал |
| `src/main.tsx` | точка входа React |
| `index.html` | шаблон страницы: заголовок вкладки, favicon, meta-теги |
| `public/` | статика: `favicon.png`, `logo.png` — копируются в корень сайта |
| `vite.config.ts` | конфиг Vite: порт dev-сервера, прокси `/api` и `/uploads` на бэкенд |
| `package.json` | зависимости и скрипты |
| `tsconfig.json` | настройки TypeScript |

## Запуск

```bash
cd front
npm install
npm run dev
```

Порт виден в терминале после запуска (настраивается в `vite.config.ts`, `server.port`).

В dev-режиме запросы `/api/*` и `/uploads/*` автоматически проксируются на бэкенд `http://localhost:8000` — поэтому перед открытием сайта запусти бэкенд (см. `back/README.md`).

## Сборка

```bash
npm run build     # продакшен-сборка в папку dist/
npm run preview   # локальный просмотр сборки
```

Папку `dist/` раздаёт бэкенд (`main.py`), она же собирается в Docker-сервисе `frontend`.

## Запуск в Docker (весь стек)

Из корня репозитория: `bash deploy/deploy.sh`.
Сайт — http://localhost:3000, API — http://localhost:8000.