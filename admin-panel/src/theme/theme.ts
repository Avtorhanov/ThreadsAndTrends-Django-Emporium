import { useCallback, useEffect, useState } from "react";

/** Тема панели: «как в системе» (без data-theme) или явная светлая/тёмная.
 * Выбор хранится в браузере; до загрузки React его применяет скрипт в index.html — без вспышки. */
export type ThemeChoice = "system" | "light" | "dark";

export const THEME_KEY = "didi-panel-theme";

export const THEME_LABELS: Record<ThemeChoice, string> = {
  system: "Как в системе",
  light: "Светлая",
  dark: "Тёмная",
};

function readChoice(): ThemeChoice {
  try {
    const value = window.localStorage.getItem(THEME_KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

export function applyTheme(choice: ThemeChoice) {
  const root = document.documentElement;
  if (choice === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", choice);
}

export function useTheme() {
  const [choice, setChoice] = useState<ThemeChoice>(readChoice);

  useEffect(() => applyTheme(choice), [choice]);

  const change = useCallback((next: ThemeChoice) => {
    try {
      if (next === "system") window.localStorage.removeItem(THEME_KEY);
      else window.localStorage.setItem(THEME_KEY, next);
    } catch {
      // Хранилище недоступно (приватный режим) — тема действует до перезагрузки.
    }
    setChoice(next);
  }, []);

  return { choice, change };
}
