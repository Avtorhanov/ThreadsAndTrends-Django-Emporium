import { useCallback, useEffect, useState } from "react";

import { PANEL_PALETTES, type PanelPalette } from "./palettes";

/** Оформление панели — личный выбор сотрудника в этом браузере:
 * тема «как в системе» (без data-theme) или явная светлая/тёмная и палитра интерфейса
 * (те же, что у покупателей, кроме «Своей»; «Лайм-тек» — без data-palette).
 * До загрузки React выбор применяет public/theme-init.js — без вспышки. */
export type ThemeChoice = "system" | "light" | "dark";

export const THEME_KEY = "didi-panel-theme";
export const PALETTE_KEY = "didi-panel-palette";
export const DEFAULT_PALETTE: PanelPalette = "lime";

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

function readPalette(): PanelPalette {
  try {
    const value = window.localStorage.getItem(PALETTE_KEY);
    return PANEL_PALETTES.find((item) => item.key === value)?.key ?? DEFAULT_PALETTE;
  } catch {
    return DEFAULT_PALETTE;
  }
}

export function applyTheme(choice: ThemeChoice) {
  const root = document.documentElement;
  if (choice === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", choice);
}

export function applyPalette(palette: PanelPalette) {
  const root = document.documentElement;
  if (palette === DEFAULT_PALETTE) root.removeAttribute("data-palette");
  else root.setAttribute("data-palette", palette);
}

function store(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // Хранилище недоступно (приватный режим) — выбор действует до перезагрузки.
  }
}

// Одно состояние на все компоненты: переключатель в меню и страница «Оформление панели».
const listeners = new Set<() => void>();
let current = { choice: readChoice(), palette: readPalette() };

function publish(next: Partial<typeof current>) {
  current = { ...current, ...next };
  listeners.forEach((listener) => listener());
}

export function useTheme() {
  const [state, setState] = useState(current);

  useEffect(() => {
    const listener = () => setState(current);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  useEffect(() => applyTheme(state.choice), [state.choice]);
  useEffect(() => applyPalette(state.palette), [state.palette]);

  const change = useCallback((next: ThemeChoice) => {
    store(THEME_KEY, next === "system" ? null : next);
    publish({ choice: next });
  }, []);

  const changePalette = useCallback((next: PanelPalette) => {
    store(PALETTE_KEY, next === DEFAULT_PALETTE ? null : next);
    publish({ palette: next });
  }, []);

  return { choice: state.choice, palette: state.palette, change, changePalette };
}
