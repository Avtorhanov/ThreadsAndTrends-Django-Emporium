import { useCallback, useEffect, useRef } from "react";
import { useBlocker } from "react-router";

const MESSAGE = "Есть несохранённые изменения. Уйти без сохранения?";

/**
 * Предупреждает об уходе с несохранёнными правками: при закрытии вкладки и при переходе внутри
 * панели. `when` — флаг или функция, если «грязность» живёт в ref. Возвращает функцию «разрешить
 * следующий переход» — для программного ухода, который данные не теряет.
 */
export function useUnsavedGuard(when: boolean | (() => boolean)): () => void {
  const latest = useRef(when);
  latest.current = when;
  const allowed = useRef(false);
  const isDirty = useCallback(() => {
    if (allowed.current) return false;
    return typeof latest.current === "function" ? latest.current() : latest.current;
  }, []);

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (isDirty()) event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  const shouldBlock = useCallback(
    ({ currentLocation, nextLocation }: { currentLocation: { pathname: string }; nextLocation: { pathname: string } }) =>
      currentLocation.pathname !== nextLocation.pathname && isDirty(),
    [isDirty],
  );
  const blocker = useBlocker(shouldBlock);
  useEffect(() => {
    if (blocker.state !== "blocked") return;
    if (window.confirm(MESSAGE)) blocker.proceed();
    else blocker.reset();
  }, [blocker]);

  return useCallback(() => {
    allowed.current = true;
  }, []);
}
