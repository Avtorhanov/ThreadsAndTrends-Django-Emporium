import type { Tabs } from "expo-router";
import { type ComponentProps, useEffect, useState } from "react";
import { Keyboard, Platform, Pressable, Text, View } from "react-native";
import Animated, {
  FadeIn,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useCart } from "../cart/CartProvider";
import { fonts } from "../theme/fonts";
import { ease, motion } from "../theme/motion";
import { makeStyles, useTheme } from "../theme/ThemeProvider";
import { radius, size } from "../theme/tokens";
import { Icon, type IconName } from "./Icon";

type TabBarProps = Parameters<NonNullable<ComponentProps<typeof Tabs>["tabBar"]>>[0];

const TABS: Record<string, { label: string; icon: IconName }> = {
  index: { label: "Каталог", icon: "grid" },
  search: { label: "Поиск", icon: "search" },
  cart: { label: "Корзина", icon: "bag" },
  profile: { label: "Профиль", icon: "user" },
};

const PAD = 6;
const MAX_WIDTH = 480;

function useKeyboardShown(): boolean {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    // На Android плавающая панель поднималась бы над клавиатурой и закрывала поле ввода.
    if (Platform.OS !== "android") return;
    const show = Keyboard.addListener("keyboardDidShow", () => setShown(true));
    const hide = Keyboard.addListener("keyboardDidHide", () => setShown(false));
    return () => {
      show.remove();
      hide.remove();
    };
  }, []);
  return shown;
}

/** Плавающая тёмная нижняя панель: активная вкладка шире и с подписью, лаймовая капсула переезжает. */
export function TabBar({ state, navigation }: TabBarProps) {
  const s = useStyles();
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const reduced = useReducedMotion();
  const { count } = useCart();
  const keyboard = useKeyboardShown();
  const [width, setWidth] = useState(0);

  const routes = state.routes.filter((route) => TABS[route.name]);
  const activeIndex = Math.max(
    0,
    routes.findIndex((route) => route.key === state.routes[state.index]?.key),
  );
  const inner = Math.max(0, width - PAD * 2);
  const active = Math.min(size.navActiveWidth, inner / 2);
  const narrow = routes.length > 1 ? (inner - active) / (routes.length - 1) : inner;

  const pillLeft = useSharedValue(PAD);
  useEffect(() => {
    const target = PAD + activeIndex * narrow;
    pillLeft.value = reduced ? target : withTiming(target, { duration: motion.tabPill.ms, easing: ease.tab });
  }, [activeIndex, narrow, reduced, pillLeft]);
  const pillStyle = useAnimatedStyle(() => ({ transform: [{ translateX: pillLeft.value }] }));

  if (keyboard) return null;

  return (
    <View pointerEvents="box-none" style={[s.wrap, { bottom: 22 + insets.bottom * 0.5 }]}>
      <View
        accessibilityRole="tablist"
        style={s.bar}
        onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
      >
        {width > 0 ? <Animated.View style={[s.pill, { width: active }, pillStyle]} /> : null}
        {routes.map((route, index) => {
          const meta = TABS[route.name] ?? { label: route.name, icon: "grid" as IconName };
          const focused = index === activeIndex;
          const badge = route.name === "cart" && count > 0 ? count : 0;
          const onPress = () => {
            const event = navigation.emit({ type: "tabPress", target: route.key, canPreventDefault: true });
            if (!focused && !event.defaultPrevented) navigation.navigate(route.name, route.params);
          };
          return (
            <TabButton
              key={route.key}
              label={meta.label}
              icon={meta.icon}
              focused={focused}
              width={width > 0 ? (focused ? active : narrow) : undefined}
              badge={badge}
              ink={focused ? c.navActiveInk : c.navInk}
              reduced={reduced}
              onPress={onPress}
            />
          );
        })}
      </View>
    </View>
  );
}

function TabButton({
  label,
  icon,
  focused,
  width,
  badge,
  ink,
  reduced,
  onPress,
}: {
  label: string;
  icon: IconName;
  focused: boolean;
  width: number | undefined;
  badge: number;
  ink: string;
  reduced: boolean;
  onPress: () => void;
}) {
  const s = useStyles();
  const animatedWidth = useSharedValue(width ?? 0);
  useEffect(() => {
    if (width === undefined) return;
    animatedWidth.value = reduced
      ? width
      : withTiming(width, { duration: motion.tabPill.ms, easing: ease.tab });
  }, [width, reduced, animatedWidth]);
  const style = useAnimatedStyle(() => (width === undefined ? { flex: 1 } : { width: animatedWidth.value }));

  return (
    <Animated.View style={style}>
      <Pressable
        accessibilityRole="tab"
        accessibilityLabel={badge ? `${label}, товаров: ${badge}` : label}
        accessibilityState={{ selected: focused }}
        onPress={onPress}
        style={s.tab}
      >
        <View>
          <Icon name={icon} size={22} color={ink} />
          {badge ? (
            <View style={s.badge}>
              <Text style={s.badgeText}>{badge > 99 ? "99+" : badge}</Text>
            </View>
          ) : null}
        </View>
        {focused ? (
          <Animated.Text
            entering={reduced ? undefined : FadeIn.duration(220).delay(120)}
            style={[s.label, { color: ink }]}
          >
            {label}
          </Animated.Text>
        ) : null}
      </Pressable>
    </Animated.View>
  );
}

const useStyles = makeStyles(({ c, shadow }) => ({
  wrap: { position: "absolute", left: 16, right: 16, alignItems: "center" },
  bar: {
    width: "100%",
    maxWidth: MAX_WIDTH,
    height: size.navHeight,
    padding: PAD,
    borderRadius: radius.nav,
    backgroundColor: c.nav,
    flexDirection: "row",
    boxShadow: shadow.nav,
  },
  pill: {
    position: "absolute",
    top: PAD,
    left: 0,
    height: size.navHeight - PAD * 2,
    borderRadius: 20,
    backgroundColor: c.accent,
    boxShadow: `${shadow.accentGlow}, inset 0 1px 0 rgba(255,255,255,.55)`,
  },
  tab: {
    height: size.navHeight - PAD * 2,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    overflow: "hidden",
  },
  // Не сжимается: пока вкладка расширяется, лишнее обрезает overflow, а не многоточие.
  label: { fontFamily: fonts.text800, fontSize: 13, flexShrink: 0 },
  badge: {
    position: "absolute",
    top: -6,
    right: -10,
    minWidth: 18,
    height: 18,
    paddingHorizontal: 4,
    borderRadius: 9,
    backgroundColor: c.accent,
    alignItems: "center",
    justifyContent: "center",
    boxShadow: `0 0 0 2px ${c.nav}`,
  },
  badgeText: { fontFamily: fonts.text800, fontSize: 10, color: c.onAccent },
}));
