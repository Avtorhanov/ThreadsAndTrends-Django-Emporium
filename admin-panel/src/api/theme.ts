import { api, unwrap } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type ThemeState = Schemas["AdminTheme"];
export type ThemeInput = Schemas["AdminThemeWriteRequest"];
export type ThemePalette = Schemas["ThemePalette"];
export type PaletteKey = Schemas["PaletteKeyEnum"];
export type ThemeMode = Schemas["ThemeModeEnum"];
export type ThemeRadius = Schemas["ThemeRadiusEnum"];

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

export const RADIUS_SCALE: Record<ThemeRadius, number> = { sharp: 0.6, normal: 1, soft: 1.35 };

const URL = "/api/v1/admin/content/theme/" as const;

export const themeService = {
  get(): Promise<ThemeState> {
    return unwrap(api.GET(URL));
  },
  save(body: ThemeInput): Promise<ThemeState> {
    return unwrap(api.PUT(URL, { body }));
  },
};
