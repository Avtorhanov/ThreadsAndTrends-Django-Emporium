import { api, unwrap } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type ThemeState = Schemas["AdminTheme"];
export type ThemeInput = Schemas["AdminThemeWriteRequest"];
export type ThemePalette = Schemas["ThemePalette"];
export type PaletteKey = Schemas["PaletteKeyEnum"];
export type ThemeMode = Schemas["ThemeModeEnum"];
export type ThemeRadius = Schemas["ThemeRadiusEnum"];
export type ThemeNav = Schemas["ThemeNavEnum"];
export type ThemeText = Schemas["ThemeTextEnum"];

export const GROUP_TITLES: Record<Schemas["PaletteGroupEnum"], string> = {
  bright: "Яркие",
  calm: "Сдержанные",
  custom: "Свой выбор покупателя",
};

export const MODE_LABELS: Record<ThemeMode, string> = {
  system: "Как в системе",
  light: "Светлая",
  dark: "Тёмная",
};

export const RADIUS_LABELS: Record<ThemeRadius, string> = {
  sharp: "Острые",
  normal: "Средние",
  soft: "Мягкие",
};

export const TEXT_LABELS: Record<ThemeText, string> = { s: "Обычный", m: "Крупнее", l: "Крупный" };

export const RADIUS_SCALE: Record<ThemeRadius, number> = { sharp: 0.6, normal: 1, soft: 1.35 };

/** Нижнее меню витрины на телефоне (как content.look.NAV_LABELS). */
export const NAV_LABELS: Record<ThemeNav, string> = {
  solid: "Сплошное",
  floating: "Плавающее",
  bar: "Нижняя панель",
};

export const NAV_HINTS: Record<ThemeNav, string> = {
  solid: "Тёмная полоса от края до края, у активной вкладки — подпись",
  floating: "Тёмная капсула над страницей с отступом от краёв",
  bar: "Панель в цвет темы, подписи у всех вкладок",
};

const URL = "/api/v1/admin/content/theme/" as const;

export const themeService = {
  get(): Promise<ThemeState> {
    return unwrap(api.GET(URL));
  },
  save(body: ThemeInput): Promise<ThemeState> {
    return unwrap(api.PUT(URL, { body }));
  },
};
