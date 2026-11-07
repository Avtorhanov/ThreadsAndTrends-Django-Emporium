import { useCallback, useEffect, useState } from "react";

import {
  PANEL_ACCENTS,
  PANEL_PALETTES,
  type PanelAccent,
  type PanelPalette,
  type PanelRadius,
  PANEL_TEXT,
  type PanelText,
} from "./palettes";

/** Оформление панели — личный выбор сотрудника в этом браузере: тема, палитра (те же, что у
 * покупателей, включая «Свою» с акцентом), углы и масштаб всего интерфейса. Значение по умолчанию не
 * хранится и атрибута на <html> не ставит. До загрузки React выбор применяет
 * public/theme-init.js — без вспышки (белые списки там те же). */
export type ThemeChoice = "system" | "light" | "dark";

export const THEME_KEY = "didi-panel-theme";
export const PALETTE_KEY = "didi-panel-palette";
export const ACCENT_KEY = "didi-panel-accent";
export const RADIUS_KEY = "didi-panel-radius";
export const TEXT_KEY = "didi-panel-text";

export const DEFAULT_PALETTE: PanelPalette = "lime";
export const DEFAULT_ACCENT: PanelAccent = "lime";
export const DEFAULT_RADIUS: PanelRadius = "normal";
export const DEFAULT_TEXT: PanelText = "100";

export const THEME_LABELS: Record<ThemeChoice, string> = {
  system: "Как в системе",
  light: "Светлая",
  dark: "Тёмная",
};

export const RADIUS_LABELS: Record<PanelRadius, string> = {
  sharp: "Острые",
  normal: "Средние",
  soft: "Мягкие",
};

export { PANEL_TEXT as TEXT_VALUES };

// Прежний «Размер текста» (s/m/l) — в проценты масштаба.
const LEGACY_TEXT: Record<string, PanelText> = { s: "100", m: "115", l: "130" };

type Look = {
  choice: ThemeChoice;
  palette: PanelPalette;
  accent: PanelAccent;
  radius: PanelRadius;
  text: PanelText;
};

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function pick<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.find((item) => item === value) ?? fallback;
}

function readLook(): Look {
  return {
    choice: pick(read(THEME_KEY), ["light", "dark"] as const, "system" as ThemeChoice),
    palette: pick(read(PALETTE_KEY), PANEL_PALETTES.map((item) => item.key), DEFAULT_PALETTE),
    accent: pick(read(ACCENT_KEY), PANEL_ACCENTS.map((item) => item.key), DEFAULT_ACCENT),
    radius: pick(read(RADIUS_KEY), Object.keys(RADIUS_LABELS) as PanelRadius[], DEFAULT_RADIUS),
    text: pick(LEGACY_TEXT[read(TEXT_KEY) ?? ""] ?? read(TEXT_KEY), PANEL_TEXT, DEFAULT_TEXT),
  };
}

function setAttr(name: string, value: string | null) {
  const root = document.documentElement;
  if (value === null) root.removeAttribute(name);
  else root.setAttribute(name, value);
}

/** Атрибуты <html> по выбору: значения по умолчанию — без атрибута (как в tokens.css). */
export function applyLook(look: Look) {
  setAttr("data-theme", look.choice === "system" ? null : look.choice);
  setAttr("data-palette", look.palette === DEFAULT_PALETTE ? null : look.palette);
  setAttr("data-accent", look.palette === "custom" ? look.accent : null);
  setAttr("data-radius", look.radius === DEFAULT_RADIUS ? null : look.radius);
  setAttr("data-text", look.text === DEFAULT_TEXT ? null : look.text);
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
let current = readLook();
if (typeof document !== "undefined") applyLook(current);

function publish(next: Partial<Look>) {
  current = { ...current, ...next };
  applyLook(current);
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

  const change = useCallback((next: ThemeChoice) => {
    store(THEME_KEY, next === "system" ? null : next);
    publish({ choice: next });
  }, []);

  const changePalette = useCallback((next: PanelPalette) => {
    store(PALETTE_KEY, next === DEFAULT_PALETTE ? null : next);
    publish({ palette: next });
  }, []);

  const changeAccent = useCallback((next: PanelAccent) => {
    store(ACCENT_KEY, next === DEFAULT_ACCENT ? null : next);
    store(PALETTE_KEY, "custom");
    publish({ palette: "custom", accent: next });
  }, []);

  const changeRadius = useCallback((next: PanelRadius) => {
    store(RADIUS_KEY, next === DEFAULT_RADIUS ? null : next);
    publish({ radius: next });
  }, []);

  const changeText = useCallback((next: PanelText) => {
    store(TEXT_KEY, next === DEFAULT_TEXT ? null : next);
    publish({ text: next });
  }, []);

  const reset = useCallback(() => {
    [THEME_KEY, PALETTE_KEY, ACCENT_KEY, RADIUS_KEY, TEXT_KEY].forEach((key) => store(key, null));
    publish({
      choice: "system",
      palette: DEFAULT_PALETTE,
      accent: DEFAULT_ACCENT,
      radius: DEFAULT_RADIUS,
      text: DEFAULT_TEXT,
    });
  }, []);

  return {
    ...state,
    change,
    changePalette,
    changeAccent,
    changeRadius,
    changeText,
    reset,
  };
}
