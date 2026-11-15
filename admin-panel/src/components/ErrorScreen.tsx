import { useEffect } from "react";
import { useRouteError } from "react-router";

const RELOAD_KEY = "didi-panel-chunk-reload";
// Кусок сборки не загрузился: после обновления сервера старых файлов уже нет.
const CHUNK_ERROR = /dynamically imported module|module script failed|Failed to fetch/i;

/** Экран вместо стандартной ошибки роутера: сбой отрисовки или загрузки экрана. */
export function ErrorScreen() {
  const error = useRouteError();
  const message = error instanceof Error ? error.message : String(error ?? "");
  const stale = CHUNK_ERROR.test(message);

  useEffect(() => {
    if (!stale) return;
    // Одна автоматическая перезагрузка: если не помогла — остаётся экран с кнопкой.
    try {
      if (sessionStorage.getItem(RELOAD_KEY)) return;
      sessionStorage.setItem(RELOAD_KEY, "1");
    } catch {
      return;
    }
    window.location.reload();
  }, [stale]);

  useEffect(() => {
    if (message) console.error(error);
  }, [error, message]);

  return (
    <div className="centered" role="alert">
      <p>{stale ? "Панель обновилась — нужно перезагрузить страницу." : "Что-то пошло не так на этом экране."}</p>
      <div className="error-screen-actions">
        <button type="button" className="button" onClick={() => window.location.reload()}>
          Обновить страницу
        </button>
        <a className="button button-ghost" href={import.meta.env.BASE_URL}>
          На сводку
        </a>
      </div>
    </div>
  );
}
