/// <reference types="vite/client" />

// Глобалки, которые заводит сниппет Яндекс.Метрики из index.html:
// YM_ID — номер счётчика текущего контура (из VITE_YANDEX_METRIKA_ID),
// ym — сам API Метрики (или очередь вызовов, если tag.js ещё не догрузился).
interface Window {
  YM_ID?: string
  ym?: (...args: unknown[]) => void
}
