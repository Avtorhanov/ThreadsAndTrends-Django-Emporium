import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import Animated, {
  interpolate,
  runOnJS,
  type SharedValue,
  useAnimatedReaction,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useCart } from "../cart/CartProvider";
import { Icon } from "../components/Icon";
import { FILL, IconButton, PressScale } from "../components/ui";
import { fonts } from "../theme/fonts";
import { makeStyles, useTheme } from "../theme/ThemeProvider";
import { ease } from "../theme/motion";
import { radius, size } from "../theme/tokens";

// Размеры развёрнутой шапки (макет): отступ сверху, строка кнопок, сегменты, отступ снизу.
// Поиск — кнопкой в строке: вверху ленты поле с фильтрами выпадает под строкой (DROP),
// в свёрнутой шапке — выезжает влево из кнопки.
const TOP = 8;
const ROW = size.headerButton;
const GAP = 12;
const SEARCH = size.searchHeight;
const CHIPS = 36;
const DROP = 8 + SEARCH + 10 + CHIPS + 8;
const CATS = size.segHeight + 8;
const BOTTOM = 14;
const BOTTOM_COMPACT = 8;

const QUICK_FILTERS: { label: string; params: Record<string, string> }[] = [
  { label: "Сначала дешевле", params: { sort: "price_asc" } },
  { label: "Сначала дороже", params: { sort: "price_desc" } },
  { label: "В наличии", params: { inStock: "1" } },
];

// Запас под тени поля и сегментов внутри обрезающей обёртки.
const SHADOW_ROOM = 12;

/** Поиск и категории при сворачивании: высота → 0, прозрачность, сдвиг −10 и масштаб .96. */
function useCollapsible(progress: SharedValue<number>, full: number) {
  return useAnimatedStyle(() => ({
    height: interpolate(progress.value, [0, 1], [full + SHADOW_ROOM, 0]),
    marginTop: interpolate(progress.value, [0, 1], [GAP, 0]),
    marginBottom: interpolate(progress.value, [0, 1], [-SHADOW_ROOM, 0]),
    opacity: interpolate(progress.value, [0, 0.6], [1, 0], "clamp"),
    transform: [
      { translateY: interpolate(progress.value, [0, 1], [0, -10]) },
      { scale: interpolate(progress.value, [0, 1], [1, 0.96]) },
    ],
  }));
}

/** Полная высота развёрнутой шапки — отступ ленты сверху. */
export function useHeaderHeight(): number {
  const insets = useSafeAreaInsets();
  return insets.top + TOP + ROW + GAP + CATS + BOTTOM;
}

type Props = {
  /** 0 — развёрнута, 1 — свёрнута (анимированное значение с гистерезисом прокрутки). */
  progress: SharedValue<number>;
  search: string;
  onSearchChange: (text: string) => void;
  /** Нажатие на логотип и название — наверх ленты. */
  onTitlePress: () => void;
  categories: ReactNode;
};

/**
 * Стеклянная шапка каталога: логотип, лаймовая кнопка поиска, тема, корзина и категории.
 * Вверху ленты поиск с фильтрами выпадает под строкой кнопок; при прокрутке категории
 * сворачиваются, название уменьшается, а поле поиска выезжает из кнопки поверх строки шапки.
 */
export function GlassHeader({ progress, search, onSearchChange, onTitlePress, categories }: Props) {
  const s = useStyles();
  const { c, dark, toggle } = useTheme();
  const { count } = useCart();
  const insets = useSafeAreaInsets();
  const reduced = useReducedMotion();
  const [focused, setFocused] = useState(false);
  const [quickOpen, setQuickOpen] = useState(false);
  const [dropOpen, setDropOpen] = useState(false);
  const [rowWidth, setRowWidth] = useState(0);
  // Свёрнутая шапка: поле поиска и категории не принимают касания, фокус и не читаются диктором.
  const [compact, setCompact] = useState(false);
  const quickInput = useRef<TextInput>(null);
  const quick = useSharedValue(0);
  const drop = useSharedValue(0);
  const dropInput = useRef<TextInput>(null);

  const submit = () => {
    const q = search.trim();
    router.navigate({ pathname: "/search", params: q ? { q } : {} });
  };

  const openQuick = () => setQuickOpen(true);
  const onSearchPress = () => {
    if (compact) openQuick();
    else setDropOpen((open) => !open);
  };
  const quickFilter = (extra: Record<string, string>) => {
    const q = search.trim();
    setDropOpen(false);
    router.navigate({ pathname: "/search", params: { ...(q ? { q } : {}), ...extra } });
  };
  const closeQuick = () => {
    quickInput.current?.blur();
    setQuickOpen(false);
  };
  useEffect(() => {
    quick.value = reduced ? Number(quickOpen) : withTiming(Number(quickOpen), { duration: 320, easing: ease.soft });
    if (quickOpen) {
      // Фокус — после того как поле выехало, иначе клавиатура дёргает раскладку.
      const timer = setTimeout(() => quickInput.current?.focus(), reduced ? 0 : 200);
      return () => clearTimeout(timer);
    }
  }, [quickOpen, reduced, quick]);
  useEffect(() => {
    drop.value = reduced ? Number(dropOpen) : withTiming(Number(dropOpen), { duration: 280, easing: ease.soft });
    if (dropOpen) {
      const timer = setTimeout(() => dropInput.current?.focus(), reduced ? 0 : 160);
      return () => clearTimeout(timer);
    }
    dropInput.current?.blur();
  }, [dropOpen, reduced, drop]);
  // Шапка развернулась (прокрутили к началу) — выехавшее поле убирается, видно полное поле поиска.
  useAnimatedReaction(
    () => progress.value < 0.5,
    (expanded, previous) => {
      if (expanded === previous) return;
      runOnJS(setCompact)(!expanded);
      if (expanded && previous === false) runOnJS(setQuickOpen)(false);
      if (!expanded) runOnJS(setDropOpen)(false);
    },
  );
  const hidden = {
    pointerEvents: compact ? ("none" as const) : ("auto" as const),
    "aria-hidden": compact,
    accessibilityElementsHidden: compact,
    importantForAccessibility: compact ? ("no-hide-descendants" as const) : ("auto" as const),
  };

  const container = useAnimatedStyle(() => ({
    paddingTop: insets.top + interpolate(progress.value, [0, 1], [TOP, 0]),
    paddingBottom: interpolate(progress.value, [0, 1], [BOTTOM, BOTTOM_COMPACT]),
  }));
  const shadowLayer = useAnimatedStyle(() => ({ opacity: progress.value }));
  const button = useAnimatedStyle(() => {
    const side = interpolate(progress.value, [0, 1], [size.headerButton, size.headerButtonCompact]);
    return { width: side, height: side, borderRadius: interpolate(progress.value, [0, 1], [16, 13]) };
  });
  const wordmark = useAnimatedStyle(() => ({ fontSize: interpolate(progress.value, [0, 1], [24, 16]) }));

  // Поле «быстрого поиска» растёт из лаймовой кнопки справа на всю строку шапки.
  const quickStyle = useAnimatedStyle(() => {
    const t = quick.value * progress.value;
    return {
      width: interpolate(t, [0, 1], [size.headerButtonCompact, Math.max(rowWidth, size.headerButtonCompact)]),
      opacity: interpolate(t, [0, 0.15], [0, 1], "clamp"),
    };
  });
  const quickContent = useAnimatedStyle(() => ({ opacity: interpolate(quick.value, [0.5, 1], [0, 1], "clamp") }));
  const catsStyle = useCollapsible(progress, CATS);
  // Выпадающий поиск: раскрывается только в развёрнутой шапке.
  const dropStyle = useAnimatedStyle(() => {
    const t = drop.value * (1 - progress.value);
    return {
      height: interpolate(t, [0, 1], [0, DROP + SHADOW_ROOM]),
      marginTop: interpolate(t, [0, 1], [0, GAP]),
      marginBottom: interpolate(t, [0, 1], [0, -SHADOW_ROOM]),
      opacity: interpolate(t, [0, 0.6], [0, 1], "clamp"),
      transform: [{ translateY: interpolate(t, [0, 1], [-8, 0]) }],
    };
  });
  const dropShown = dropOpen && !compact;
  const dropHidden = {
    pointerEvents: dropShown ? ("auto" as const) : ("none" as const),
    "aria-hidden": !dropShown,
    accessibilityElementsHidden: !dropShown,
    importantForAccessibility: dropShown ? ("auto" as const) : ("no-hide-descendants" as const),
  };

  return (
    <Animated.View style={[s.header, container]}>
      <Animated.View pointerEvents="none" style={[s.shadow, shadowLayer]} />
      {/* Стекло: blur на iOS и в браузере; на Android — полупрозрачный фон (blur там дорогой). */}
      {Platform.OS === "android" ? (
        <View pointerEvents="none" style={[s.glassFill, { backgroundColor: c.glass }]} />
      ) : (
        <BlurView pointerEvents="none" intensity={40} tint={dark ? "dark" : "light"} style={s.glassFill}>
          <View style={[StyleSheet.absoluteFill, { backgroundColor: c.glass }]} />
        </BlurView>
      )}

      <View style={s.row} onLayout={(event) => setRowWidth(event.nativeEvent.layout.width)}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="DiDi-shop, наверх"
          onPress={onTitlePress}
          style={({ pressed }) => [s.brand, pressed && s.pressed]}
        >
          <Animated.View style={[s.logo, button]}>
            <Text style={s.logoText}>DiDi</Text>
          </Animated.View>
          {/* Логотип как на сайте и в панели: плашка «DiDi» + «shop». */}
          <Animated.Text style={[s.word, wordmark]}>
            <Text style={s.wordAccent}>shop</Text>
          </Animated.Text>
        </Pressable>
        <View style={s.actions}>
          <Animated.View style={[s.searchButtonWrap, button]}>
            <PressScale
              accessibilityRole="button"
              accessibilityLabel="Поиск"
              accessibilityState={{ expanded: dropShown || quickOpen }}
              onPress={onSearchPress}
              scale={0.92}
              style={[s.searchButton, dropShown && s.searchButtonOn]}
            >
              <Icon name="search" size={21} color={dropShown ? c.segOnInk : c.onAccent} strokeWidth={2.2} />
            </PressScale>
          </Animated.View>
          <Animated.View style={[s.buttonWrap, button]}>
            <IconButton
              icon={dark ? "sun" : "moon"}
              label={dark ? "Светлая тема" : "Тёмная тема"}
              onPress={toggle}
              style={s.buttonFill}
            />
          </Animated.View>
          <Animated.View style={[s.buttonWrap, button]}>
            <IconButton
              icon="bag"
              label="Корзина"
              badge={count}
              onPress={() => router.navigate("/cart")}
              style={s.buttonFill}
            />
          </Animated.View>
        </View>

        {quickOpen ? (
          <Animated.View style={[s.quick, quickStyle]}>
            <Animated.View style={[s.quickInner, quickContent]}>
              <Icon name="search" size={19} color={c.muted} />
              <TextInput
                ref={quickInput}
                value={search}
                onChangeText={onSearchChange}
                onSubmitEditing={submit}
                placeholder="Найти товар"
                placeholderTextColor={c.muted}
                selectionColor={c.brand}
                accessibilityLabel="Быстрый поиск"
                returnKeyType="search"
                autoCorrect={false}
                maxLength={100}
                style={s.quickInput}
              />
              <PressScale
                accessibilityRole="button"
                accessibilityLabel="Закрыть поиск"
                onPress={closeQuick}
                hitSlop={4}
                scale={0.9}
                style={s.quickClose}
              >
                <Icon name="close" size={18} color={c.ink} />
              </PressScale>
            </Animated.View>
          </Animated.View>
        ) : null}
      </View>

      <Animated.View {...dropHidden} style={[s.clip, dropStyle]}>
        <View style={s.drop}>
          <View style={[s.search, focused && s.searchFocused]}>
            <Icon name="search" size={20} color={c.muted} />
            <TextInput
              ref={dropInput}
              value={search}
              onChangeText={onSearchChange}
              onSubmitEditing={submit}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder="Футболка, термос, плед…"
              placeholderTextColor={c.muted}
              selectionColor={c.brand}
              accessibilityLabel="Поиск по каталогу"
              returnKeyType="search"
              autoCorrect={false}
              maxLength={100}
              style={s.searchInput}
            />
            <PressScale
              accessibilityRole="button"
              accessibilityLabel="Фильтры и сортировка"
              onPress={() => router.navigate({ pathname: "/search", params: { filters: "1" } })}
              hitSlop={2}
              style={s.filter}
            >
              <Icon name="filter" size={18} color={c.onAccent} strokeWidth={2.2} />
            </PressScale>
          </View>
          <View style={s.chips}>
            {QUICK_FILTERS.map((chip) => (
              <PressScale
                key={chip.label}
                accessibilityRole="button"
                onPress={() => quickFilter(chip.params)}
                scale={0.96}
                style={s.chip}
              >
                <Text style={s.chipText}>{chip.label}</Text>
              </PressScale>
            ))}
          </View>
        </View>
      </Animated.View>

      <Animated.View {...hidden} style={[s.clip, catsStyle]}>
        {categories}
      </Animated.View>
    </Animated.View>
  );
}

/**
 * Лента растворяется под шапкой: градиентная подложка цвета фона поверх ленты (вместо маски —
 * дешевле на Android и одинаково в браузере). Развёрнута: непрозрачно до 110 → прозрачно к 236.
 */
export function FeedFade({ progress }: { progress: SharedValue<number> }) {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const style = useAnimatedStyle(() => ({
    height: insets.top + interpolate(progress.value, [0, 1], [236, 92]),
  }));
  return (
    <Animated.View pointerEvents="none" style={[styles.fade, style]}>
      <LinearGradient
        colors={[c.bg, c.bg, `${c.bg}00`]}
        locations={[0, 0.45, 1]}
        style={StyleSheet.absoluteFill}
      />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  fade: { position: "absolute", top: 0, left: 0, right: 0, zIndex: 2 },
});

const useStyles = makeStyles(({ c, shadow }) => ({
  header: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    zIndex: 3,
    paddingHorizontal: 18,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
  },
  glassFill: {
    ...FILL,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    overflow: "hidden",
  },
  shadow: {
    ...FILL,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    borderBottomWidth: 1,
    borderColor: c.glassLine,
    boxShadow: shadow.header,
  },
  row: { height: ROW, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  brand: { flexDirection: "row", alignItems: "center", gap: 10, flexShrink: 1, minHeight: size.touchMin },
  pressed: { opacity: 0.7 },
  quick: {
    position: "absolute",
    right: 0,
    top: (ROW - size.headerButtonCompact - 6) / 2,
    height: size.headerButtonCompact + 6,
    borderRadius: 15,
    borderWidth: 1.5,
    borderColor: c.brand,
    backgroundColor: c.surface,
    boxShadow: shadow.control,
    overflow: "hidden",
  },
  quickInner: { flex: 1, flexDirection: "row", alignItems: "center", gap: 8, paddingLeft: 12, paddingRight: 4 },
  quickInput: {
    outlineWidth: 0,
    outlineStyle: "solid", // при "auto" Chrome рисует обводку фокуса даже с толщиной 0
    flex: 1,
    minWidth: 0,
    height: "100%",
    fontFamily: fonts.text600,
    fontSize: 15,
    color: c.ink,
  },
  quickClose: { width: 36, height: 36, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  logo: {
    backgroundColor: c.brand,
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 12px 22px -8px rgba(31,77,58,.75), inset 0 1px 0 rgba(255,255,255,.3)",
  },
  logoText: { fontFamily: fonts.display700, fontSize: 12, letterSpacing: -0.5, color: c.brandInk },
  word: { fontFamily: fonts.display700, letterSpacing: -0.5, color: c.ink },
  wordAccent: { color: c.brand },
  actions: { flexDirection: "row", alignItems: "center", gap: 10 },
  searchButtonWrap: { overflow: "hidden", boxShadow: shadow.accentGlow },
  searchButton: {
    width: "100%",
    height: "100%",
    backgroundColor: c.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  searchButtonOn: { backgroundColor: c.segOnBg },
  drop: {
    gap: 10,
    padding: 8,
    borderRadius: radius.card,
    backgroundColor: c.surface,
    boxShadow: shadow.card,
  },
  chips: { flexDirection: "row", gap: 6, height: CHIPS },
  chip: {
    height: CHIPS,
    paddingHorizontal: 12,
    borderRadius: radius.seg,
    backgroundColor: c.bg,
    alignItems: "center",
    justifyContent: "center",
  },
  chipText: { fontFamily: fonts.text800, fontSize: 13, color: c.ink },
  buttonWrap: { overflow: "visible" },
  buttonFill: { width: "100%", height: "100%" },
  clip: {
    overflow: "hidden",
    marginHorizontal: -SHADOW_ROOM,
    paddingHorizontal: SHADOW_ROOM,
    paddingBottom: SHADOW_ROOM,
  },
  searchFocused: { borderColor: c.brand },
  search: {
    borderWidth: 1.5,
    borderColor: "transparent",
    height: SEARCH,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingLeft: 16,
    paddingRight: 6,
    borderRadius: radius.search,
    backgroundColor: c.bg,
  },
  searchInput: {
    outlineWidth: 0,
    outlineStyle: "solid", // при "auto" Chrome рисует обводку фокуса даже с толщиной 0
    flex: 1,
    minWidth: 0,
    height: SEARCH,
    fontFamily: fonts.text600,
    fontSize: 15,
    color: c.ink,
  },
  filter: {
    width: 40,
    height: 40,
    borderRadius: 13,
    backgroundColor: c.accent,
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 8px 14px -6px rgba(130,180,0,.8)",
  },
}));
