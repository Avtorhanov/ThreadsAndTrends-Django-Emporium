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

import { motion } from "./motion";
import { type Palette, palettes, type Shadows, shadows, type ThemeName } from "./tokens";

export type ThemePreference = "system" | ThemeName;

export type Theme = {
  name: ThemeName;
  dark: boolean;
  c: Palette;
  shadow: Shadows;
};

type ThemeContextValue = Theme & {
  preference: ThemePreference;
  setPreference: (preference: ThemePreference) => void;
  /** Кнопка в шапке: явно переключает на противоположную текущей. */
  toggle: () => void;
};

const STORAGE_KEY = "didi:theme";

export function buildTheme(name: ThemeName): Theme {
  return { name, dark: name === "dark", c: palettes[name], shadow: shadows[name] };
}

const THEMES: Record<ThemeName, Theme> = { light: buildTheme("light"), dark: buildTheme("dark") };

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const system = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>("system");

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((value) => {
        if (value === "light" || value === "dark" || value === "system") setPreferenceState(value);
      })
      .catch(() => undefined);
  }, []);

  const name: ThemeName = preference === "system" ? (system === "dark" ? "dark" : "light") : preference;

  const setPreference = useCallback((next: ThemePreference) => {
    setPreferenceState(next);
    AsyncStorage.setItem(STORAGE_KEY, next).catch(() => undefined);
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({
      ...THEMES[name],
      preference,
      setPreference,
      toggle: () => setPreference(name === "dark" ? "light" : "dark"),
    }),
    [name, preference, setPreference],
  );

  return (
    <ThemeContext.Provider value={value}>
      {children}
      <ThemeFade theme={THEMES[name]} />
    </ThemeContext.Provider>
  );
}

/**
 * Смена темы анимируется (motion.theme, 450 мс): поверх экрана на мгновение остаётся фон
 * прежней темы и плавно растворяется. Анимировать каждый цвет в каждом компоненте дороже.
 */
function ThemeFade({ theme }: { theme: Theme }) {
  const reduced = useReducedMotion();
  const last = useRef<ThemeName>(theme.name);
  const [fadeColor, setFadeColor] = useState<string>(theme.c.bg);
  const opacity = useSharedValue(0);

  useEffect(() => {
    if (last.current === theme.name) return;
    const from = palettes[last.current].bg;
    last.current = theme.name;
    if (reduced) return;
    setFadeColor(from);
    opacity.value = 0.9;
    opacity.value = withTiming(0, { duration: motion.theme.ms });
  }, [theme.name, reduced, opacity]);

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

/**
 * Стили, зависящие от темы: `const useStyles = makeStyles((t) => ({ ... }))`, в компоненте —
 * `const s = useStyles()`. Таблица стилей создаётся один раз на тему.
 */
export function makeStyles<T extends StyleSheet.NamedStyles<T>>(factory: (theme: Theme) => T) {
  const cache: Partial<Record<ThemeName, T>> = {};
  return function useStyles(): T {
    const { name } = useTheme();
    if (!cache[name]) cache[name] = StyleSheet.create(factory(THEMES[name]));
    return cache[name] as T;
  };
}
