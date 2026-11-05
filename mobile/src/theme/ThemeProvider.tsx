import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { StyleSheet, useColorScheme } from "react-native";
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";

import { api, unwrap } from "../api/client";
import type { components } from "../api/schema";
import { motion } from "./motion";
import {
  type AccentName,
  accentShadows,
  accents,
  type Palette,
  type PaletteName,
  paletteList,
  paletteShadows,
  paletteThemes,
  type RadiusMode,
  radiusScale,
  type Shadows,
  type TextMode,
  type ThemeName,
  textScale,
} from "./tokens";

export type ThemePreference = "system" | ThemeName;

/** Выбор покупателя: палитра, акцент «Своей», углы, размер текста. */
export type Look = { palette: PaletteName; accent: AccentName; radius: RadiusMode; text: TextMode };

export type Theme = {
  name: ThemeName;
  dark: boolean;
  c: Palette;
  shadow: Shadows;
  look: Look;
  /** Ключ таблиц стилей: тема + выбор покупателя. */
  key: string;
};

type ShopTheme = components["schemas"]["ShopTheme"];

type ThemeContextValue = Theme & {
  preference: ThemePreference;
  setPreference: (preference: ThemePreference) => void;
  /** Кнопка в шапке: явно переключает на противоположную текущей. */
  toggle: () => void;
  setLook: (changes: Partial<Look>) => void;
  /** Палитры, которые администратор разрешил покупателям (панель → «Тема»). */
  palettes: PaletteName[];
};

const STORAGE_KEY = "didi:theme";
const LOOK_KEY = "didi:look";
const DEFAULT_LOOK: Look = { palette: "lime", accent: "lime", radius: "normal", text: "s" };
const ALL_PALETTES = paletteList.map((item) => item.key);

const cache = new Map<string, Theme>();

export function buildTheme(name: ThemeName, look: Look = DEFAULT_LOOK): Theme {
  const key = `${name}:${look.palette}:${look.palette === "custom" ? look.accent : ""}:${look.radius}:${look.text}`;
  const cached = cache.get(key);
  if (cached) return cached;
  let c = paletteThemes[look.palette][name];
  let shadow = paletteShadows[look.palette][name];
  if (look.palette === "custom") {
    c = { ...c, ...accents[look.accent][name] };
    shadow = accentShadows[look.accent][name];
  }
  const theme: Theme = { name, dark: name === "dark", c, shadow, look, key };
  cache.set(key, theme);
  return theme;
}

function isKey<T extends string>(value: unknown, allowed: readonly T[]): value is T {
  return typeof value === "string" && (allowed as readonly string[]).includes(value);
}

const ACCENT_KEYS = Object.keys(accents) as AccentName[];
const RADIUS_KEYS = Object.keys(radiusScale) as RadiusMode[];
const TEXT_KEYS = Object.keys(textScale) as TextMode[];

/** Сохранённый выбор → только допустимые значения (хранилище могло остаться от старой версии). */
function parseLook(raw: string | null): Partial<Look> {
  if (!raw) return {};
  try {
    const value = JSON.parse(raw) as Record<string, unknown>;
    const look: Partial<Look> = {};
    if (isKey(value.palette, ALL_PALETTES)) look.palette = value.palette;
    if (isKey(value.accent, ACCENT_KEYS)) look.accent = value.accent;
    if (isKey(value.radius, RADIUS_KEYS)) look.radius = value.radius;
    if (isKey(value.text, TEXT_KEYS)) look.text = value.text;
    return look;
  } catch {
    return {};
  }
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const system = useColorScheme();
  const [stored, setStored] = useState<ThemePreference | null>(null);
  const [chosen, setChosen] = useState<Partial<Look>>({});
  const [shop, setShop] = useState<ShopTheme | null>(null);

  useEffect(() => {
    AsyncStorage.multiGet([STORAGE_KEY, LOOK_KEY])
      .then((pairs) => {
        const theme = pairs[0]?.[1] ?? null;
        if (theme === "light" || theme === "dark" || theme === "system") setStored(theme);
        setChosen(parseLook(pairs[1]?.[1] ?? null));
      })
      .catch(() => undefined);
    // Что разрешил администратор; без сети — все палитры и значения по умолчанию.
    unwrap(api.GET("/api/v1/content/theme/"))
      .then(setShop)
      .catch(() => undefined);
  }, []);

  const palettes = useMemo(
    () =>
      shop
        ? shop.palettes.map((item) => item.key).filter((key): key is PaletteName => isKey(key, ALL_PALETTES))
        : ALL_PALETTES,
    [shop],
  );
  const preference: ThemePreference = stored ?? shop?.default_mode ?? "system";
  const name: ThemeName = preference === "system" ? (system === "dark" ? "dark" : "light") : preference;
  const defaultPalette = shop && isKey(shop.default_palette, palettes) ? shop.default_palette : DEFAULT_LOOK.palette;
  const look: Look = {
    // Палитру могли выключить в панели — тогда палитра магазина по умолчанию.
    palette: chosen.palette && palettes.includes(chosen.palette) ? chosen.palette : defaultPalette,
    accent: chosen.accent ?? DEFAULT_LOOK.accent,
    radius: chosen.radius ?? (shop && isKey(shop.default_radius, RADIUS_KEYS) ? shop.default_radius : "normal"),
    text: chosen.text ?? (shop && isKey(shop.default_text, TEXT_KEYS) ? shop.default_text : DEFAULT_LOOK.text),
  };
  const theme = buildTheme(name, look);

  const setPreference = useCallback((next: ThemePreference) => {
    setStored(next);
    AsyncStorage.setItem(STORAGE_KEY, next).catch(() => undefined);
  }, []);

  const setLook = useCallback((changes: Partial<Look>) => {
    setChosen((prev) => {
      const next = { ...prev, ...changes };
      AsyncStorage.setItem(LOOK_KEY, JSON.stringify(next)).catch(() => undefined);
      return next;
    });
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({
      ...theme,
      preference,
      setPreference,
      setLook,
      palettes,
      toggle: () => setPreference(theme.name === "dark" ? "light" : "dark"),
    }),
    [theme, preference, setPreference, setLook, palettes],
  );

  return (
    <ThemeContext.Provider value={value}>
      {children}
      <ThemeFade theme={theme} />
    </ThemeContext.Provider>
  );
}

/**
 * Смена темы или палитры анимируется (motion.theme, 450 мс): поверх экрана на мгновение
 * остаётся фон прежнего вида и плавно растворяется. Анимировать каждый цвет дороже.
 */
function ThemeFade({ theme }: { theme: Theme }) {
  const reduced = useReducedMotion();
  const last = useRef<Theme>(theme);
  const [fadeColor, setFadeColor] = useState<string>(theme.c.bg);
  const opacity = useSharedValue(0);

  useEffect(() => {
    const previous = last.current;
    last.current = theme;
    if (previous.key === theme.key || previous.c.bg === theme.c.bg || reduced) return;
    setFadeColor(previous.c.bg);
    opacity.value = 0.9;
    opacity.value = withTiming(0, { duration: motion.theme.ms });
  }, [theme, reduced, opacity]);

  const style = useAnimatedStyle(() => ({ opacity: opacity.value }));
  return (
    <Animated.View
      pointerEvents="none"
      style={[StyleSheet.absoluteFill, { backgroundColor: fadeColor }, style]}
    />
  );
}

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error("useTheme вне ThemeProvider");
  return value;
}

const RADIUS_PROPS = [
  "borderRadius",
  "borderTopLeftRadius",
  "borderTopRightRadius",
  "borderBottomLeftRadius",
  "borderBottomRightRadius",
] as const;

type StyleRecord = Record<string, unknown>;

/**
 * Углы и размер текста покупателя — одним местом для всех экранов: радиусы умножаются на
 * масштаб углов (круги остаются кругами), кегль и интерлиньяж — на масштаб текста.
 */
function scaleStyles<T>(styles: T, look: Look): T {
  const r = radiusScale[look.radius];
  const t = textScale[look.text];
  if (r === 1 && t === 1) return styles;
  const result: Record<string, StyleRecord> = {};
  for (const [name, raw] of Object.entries(styles as Record<string, StyleRecord>)) {
    const style: StyleRecord = { ...raw };
    const width = typeof style.width === "number" ? style.width : null;
    const height = typeof style.height === "number" ? style.height : null;
    const side = width !== null && height !== null ? Math.min(width, height) : null;
    for (const prop of RADIUS_PROPS) {
      const value = style[prop];
      if (typeof value !== "number" || r === 1) continue;
      if (side !== null && value * 2 >= side) continue; // круг или «пилюля» — форма важнее
      style[prop] = Math.round(value * r);
    }
    if (t !== 1) {
      if (typeof style.fontSize === "number") style.fontSize = Math.round(style.fontSize * t * 2) / 2;
      if (typeof style.lineHeight === "number") style.lineHeight = Math.round(style.lineHeight * t);
    }
    result[name] = style;
  }
  return result as T;
}

/**
 * Стили, зависящие от темы: `const useStyles = makeStyles((t) => ({ ... }))`, в компоненте —
 * `const s = useStyles()`. Таблица стилей создаётся один раз на тему и выбор покупателя.
 */
export function makeStyles<T extends StyleSheet.NamedStyles<T>>(factory: (theme: Theme) => T) {
  const tables = new Map<string, T>();
  return function useStyles(): T {
    const theme = useTheme();
    let table = tables.get(theme.key);
    if (!table) {
      table = StyleSheet.create(scaleStyles(factory(theme), theme.look)) as T;
      tables.set(theme.key, table);
    }
    return table;
  };
}
