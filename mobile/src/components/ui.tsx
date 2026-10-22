import { LinearGradient } from "expo-linear-gradient";
import { type ReactNode, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  type PressableProps,
  ScrollView,
  type StyleProp,
  StyleSheet,
  Text,
  TextInput,
  type TextInputProps,
  View,
  type ViewStyle,
} from "react-native";
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";
import { SafeAreaView } from "react-native-safe-area-context";

import { fonts } from "../theme/fonts";
import { ease, motion } from "../theme/motion";
import { makeStyles, useTheme } from "../theme/ThemeProvider";
import { radius, size, space } from "../theme/tokens";
import { Icon, type IconName } from "./Icon";

/** Нижний отступ экранов во вкладках: плавающая панель (70) + отступ снизу (22) + зазор. */
export const TAB_BAR_SPACE = size.navHeight + 22 + 24;

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

type PressScaleProps = Omit<PressableProps, "style"> & {
  style?: StyleProp<ViewStyle>;
  scale?: number;
  children?: ReactNode;
};

/** Нажатие — масштаб .96 за 180 мс (motion.press); при «Уменьшить движение» — прозрачность. */
export function PressScale({ style, scale = motion.press.scale, onPressIn, onPressOut, children, ...props }: PressScaleProps) {
  const reduced = useReducedMotion();
  const pressed = useSharedValue(0);
  const animated = useAnimatedStyle(() =>
    reduced
      ? { opacity: 1 - pressed.value * 0.3 }
      : { transform: [{ scale: 1 - pressed.value * (1 - scale) }] },
  );
  return (
    <AnimatedPressable
      {...props}
      onPressIn={(event) => {
        pressed.value = withTiming(1, { duration: motion.press.ms, easing: ease.out });
        onPressIn?.(event);
      }}
      onPressOut={(event) => {
        pressed.value = withTiming(0, { duration: motion.press.ms, easing: ease.out });
        onPressOut?.(event);
      }}
      style={[style, animated]}
    >
      {children}
    </AnimatedPressable>
  );
}

/** Карточка: белая с многослойной тенью; в тёмной теме — диагональный перелив cardStops. */
export function Card({
  children,
  style,
  radius: cornerRadius = radius.card,
}: {
  children?: ReactNode;
  style?: StyleProp<ViewStyle>;
  radius?: number;
}) {
  const { c, shadow } = useTheme();
  return (
    <View
      style={[
        { backgroundColor: c.card, borderRadius: cornerRadius, boxShadow: shadow.card },
        style,
      ]}
    >
      <CardGradient radius={cornerRadius} />
      {children}
    </View>
  );
}

/** Диагональный перелив карточки в тёмной теме (cardStops, 165°); в светлой — ничего. */
export function CardGradient({ radius: cornerRadius = radius.card }: { radius?: number }) {
  const { c } = useTheme();
  if (!c.cardStops) return null;
  return (
    <LinearGradient
      pointerEvents="none"
      colors={c.cardStops}
      locations={[0, 0.45, 1]}
      // 165° в CSS: почти вертикально, слегка слева направо.
      start={{ x: 0.37, y: 0 }}
      end={{ x: 0.63, y: 1 }}
      style={[StyleSheet.absoluteFill, { borderRadius: cornerRadius }]}
    />
  );
}

export function Screen({
  title,
  overline,
  children,
  tabs,
  edges = ["bottom"],
}: {
  title?: string;
  overline?: string;
  children: ReactNode;
  /** Экран во вкладке: снизу место под плавающую панель, сверху — безопасная зона. */
  tabs?: boolean;
  edges?: ("top" | "bottom")[];
}) {
  const s = useStyles();
  return (
    <SafeAreaView style={s.safe} edges={tabs ? ["top"] : edges}>
      <KeyboardAvoidingView style={s.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView
          contentContainerStyle={[s.content, tabs && { paddingBottom: TAB_BAR_SPACE }]}
          keyboardShouldPersistTaps="handled"
        >
          {title ? <ScreenTitle title={title} overline={overline} /> : null}
          {children}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

/** Заголовок раздела: надзаголовок 12 caps + Unbounded 28. */
export function ScreenTitle({ title, overline }: { title: string; overline?: string }) {
  const s = useStyles();
  return (
    <View style={s.titleBox}>
      {overline ? <Text style={s.overline}>{overline}</Text> : null}
      <Text style={s.title} accessibilityRole="header">
        {title}
      </Text>
    </View>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  const s = useStyles();
  return (
    <Text style={s.section} accessibilityRole="header">
      {children}
    </Text>
  );
}

type TextFieldProps = TextInputProps & { label: string; errors?: string[] };

export function TextField({ label, errors, style, onFocus, onBlur, ...props }: TextFieldProps) {
  const s = useStyles();
  const { c } = useTheme();
  const [focused, setFocused] = useState(false);
  const hasError = Boolean(errors?.length);
  return (
    <View style={s.field}>
      <Text style={s.label}>{label}</Text>
      <TextInput
        placeholderTextColor={c.muted}
        selectionColor={c.brand}
        style={[
          s.input,
          props.multiline && s.inputMultiline,
          focused && s.inputFocused,
          hasError && s.inputError,
          style,
        ]}
        accessibilityLabel={label}
        onFocus={(event) => {
          setFocused(true);
          onFocus?.(event);
        }}
        onBlur={(event) => {
          setFocused(false);
          onBlur?.(event);
        }}
        {...props}
      />
      {errors?.map((message) => (
        <Text key={message} style={s.fieldError}>
          {message}
        </Text>
      ))}
    </View>
  );
}

type ButtonProps = {
  title: string;
  onPress: () => void;
  loading?: boolean;
  variant?: "primary" | "secondary" | "accent" | "danger";
  disabled?: boolean;
  /** Справа в кнопке — например, сумма. */
  trailing?: string;
  icon?: IconName;
};

export function Button({
  title,
  onPress,
  loading,
  variant = "primary",
  disabled,
  trailing,
  icon,
}: ButtonProps) {
  const s = useStyles();
  const { c } = useTheme();
  const inactive = disabled || loading;
  const ink = {
    primary: c.ctaInk,
    secondary: c.ink,
    accent: c.onAccent,
    danger: c.danger,
  }[variant];
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityState={{ disabled: Boolean(inactive), busy: Boolean(loading) }}
      onPress={onPress}
      disabled={inactive}
      scale={0.98}
      style={[s.button, s[`button_${variant}`], trailing ? s.buttonSplit : null, inactive && s.buttonDimmed]}
    >
      {loading ? (
        <ActivityIndicator color={ink} />
      ) : (
        <>
          <View style={s.buttonLabel}>
            {icon ? <Icon name={icon} size={20} color={ink} /> : null}
            <Text style={[s.buttonText, { color: ink }]}>{title}</Text>
          </View>
          {trailing ? <Text style={[s.buttonTrailing, { color: ink }]}>{trailing}</Text> : null}
        </>
      )}
    </PressScale>
  );
}

export function LinkButton({ title, onPress, tone = "brand" }: { title: string; onPress: () => void; tone?: "brand" | "danger" | "muted" }) {
  const s = useStyles();
  const { c } = useTheme();
  return (
    <Pressable accessibilityRole="link" onPress={onPress} style={({ pressed }) => [s.link, pressed && s.pressed]}>
      <Text style={[s.linkText, { color: tone === "brand" ? c.brand : tone === "danger" ? c.danger : c.muted }]}>
        {title}
      </Text>
    </Pressable>
  );
}

type IconButtonProps = {
  icon: IconName;
  label: string;
  onPress?: () => void;
  badge?: number;
  variant?: "surface" | "accent" | "glass";
  /** Размер плашки; меньше 44 — касание добирается hitSlop. */
  size?: number;
  style?: StyleProp<ViewStyle>;
};

/** Квадратная иконочная кнопка (шапка, «Назад»). Касание ≥ 44 px, подпись для экранного диктора. */
export function IconButton({ icon, label, onPress, badge, variant = "surface", size: side = size.headerButton, style }: IconButtonProps) {
  const s = useStyles();
  const { c } = useTheme();
  const ink = variant === "accent" ? c.onAccent : c.ink;
  const slop = Math.max(0, Math.ceil((size.touchMin - side) / 2));
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={badge ? `${label}, товаров: ${badge}` : label}
      onPress={onPress}
      hitSlop={slop}
      scale={0.92}
      style={[s.iconButton, s[`icon_${variant}`], { width: side, height: side }, style]}
    >
      <Icon name={icon} size={21} color={ink} strokeWidth={variant === "accent" ? 2.2 : 2} />
      {badge ? (
        <View style={s.badge}>
          <Text style={s.badgeText}>{badge > 99 ? "99+" : badge}</Text>
        </View>
      ) : null}
    </PressScale>
  );
}

export function Message({
  text,
  kind = "error",
}: {
  text: string | null;
  kind?: "error" | "success" | "warning" | "info";
}) {
  const s = useStyles();
  const { c } = useTheme();
  if (!text) return null;
  const palette = {
    error: [c.danger, c.dangerBg],
    success: [c.success, c.successBg],
    warning: [c.warning, c.warningBg],
    info: [c.info, c.infoBg],
  }[kind];
  return (
    <View
      style={[s.message, { backgroundColor: palette[1] }]}
      accessibilityRole={kind === "error" ? "alert" : undefined}
      accessibilityLiveRegion="polite"
    >
      <Text style={[s.messageText, { color: palette[0] }]}>{text}</Text>
    </View>
  );
}

export function Hint({ children }: { children: ReactNode }) {
  const s = useStyles();
  return <Text style={s.hint}>{children}</Text>;
}

/** Строка «подпись — значение» (итоги корзины, заказа). */
export function SummaryRow({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  const s = useStyles();
  return (
    <View style={s.row}>
      <Text style={[s.rowLabel, strong && s.rowStrongLabel]}>{label}</Text>
      <Text style={[s.rowValue, strong && s.rowStrong]}>{value}</Text>
    </View>
  );
}

export function Divider() {
  const s = useStyles();
  return <View style={s.divider} />;
}

export function Loading() {
  const { c } = useTheme();
  return <ActivityIndicator color={c.ink} />;
}

/** Экран-заглушка по центру: загрузка, ошибка, пустое состояние. */
export function Centered({ children }: { children: ReactNode }) {
  const s = useStyles();
  return <View style={s.center}>{children}</View>;
}

const useStyles = makeStyles(({ c, shadow }) => ({
  safe: { flex: 1, backgroundColor: c.bg },
  flex: { flex: 1 },
  content: { padding: space.screen, gap: 16, flexGrow: 1 },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    padding: space.screen,
    backgroundColor: c.bg,
  },
  titleBox: { gap: 6, paddingTop: 8, paddingBottom: 4 },
  overline: {
    fontFamily: fonts.text800,
    fontSize: 12,
    letterSpacing: 1.7,
    textTransform: "uppercase",
    color: c.muted,
  },
  title: { fontFamily: fonts.display700, fontSize: 28, lineHeight: 32, letterSpacing: -0.5, color: c.ink },
  section: { fontFamily: fonts.display700, fontSize: 18, letterSpacing: -0.3, color: c.ink, marginTop: 8 },
  field: { gap: 6 },
  label: { fontFamily: fonts.text700, fontSize: 13, color: c.muted },
  input: {
    minHeight: size.searchHeight,
    backgroundColor: c.surface,
    borderRadius: radius.control,
    borderWidth: 1.5,
    borderColor: c.inputLine,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontFamily: fonts.text600,
    fontSize: 16,
    color: c.ink,
  },
  inputMultiline: { minHeight: 88, textAlignVertical: "top" },
  inputFocused: { borderColor: c.brand },
  inputError: { borderColor: c.danger },
  fieldError: { fontFamily: fonts.text600, color: c.danger, fontSize: 13 },
  button: {
    minHeight: 56,
    borderRadius: radius.cta,
    paddingHorizontal: 22,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
  },
  buttonSplit: { justifyContent: "space-between" },
  button_primary: { backgroundColor: c.ctaBg, boxShadow: "0 20px 32px -14px rgba(0,0,0,.6)" },
  button_secondary: { backgroundColor: c.surface, boxShadow: shadow.control },
  button_accent: { backgroundColor: c.accent, boxShadow: shadow.accentGlow },
  button_danger: { backgroundColor: c.dangerBg },
  buttonDimmed: { opacity: 0.55 },
  buttonLabel: { flexDirection: "row", alignItems: "center", gap: 8 },
  buttonText: { fontFamily: fonts.text800, fontSize: 16 },
  buttonTrailing: { fontFamily: fonts.display700, fontSize: 15 },
  link: { minHeight: size.touchMin, paddingHorizontal: 8, alignItems: "center", justifyContent: "center" },
  linkText: { fontFamily: fonts.text700, fontSize: 15 },
  pressed: { opacity: 0.6 },
  iconButton: { borderRadius: radius.control, alignItems: "center", justifyContent: "center" },
  icon_surface: { backgroundColor: c.surface, boxShadow: shadow.control },
  icon_accent: {
    backgroundColor: c.accent,
    boxShadow: "0 10px 18px -8px rgba(130,180,0,.8), inset 0 1px 0 rgba(255,255,255,.5)",
  },
  icon_glass: { backgroundColor: c.btnGlass, boxShadow: shadow.control },
  badge: {
    position: "absolute",
    top: -4,
    right: -4,
    minWidth: 20,
    height: 20,
    paddingHorizontal: 5,
    borderRadius: 10,
    backgroundColor: c.accent,
    alignItems: "center",
    justifyContent: "center",
    boxShadow: `0 0 0 2px ${c.bg}`,
  },
  badgeText: { fontFamily: fonts.text800, fontSize: 11, color: c.onAccent },
  message: { borderRadius: radius.control, paddingHorizontal: 16, paddingVertical: 12 },
  messageText: { fontFamily: fonts.text600, fontSize: 14, lineHeight: 20 },
  hint: { fontFamily: fonts.text500, color: c.muted, fontSize: 14, lineHeight: 20 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 16 },
  rowLabel: { fontFamily: fonts.text600, fontSize: 15, color: c.muted, flexShrink: 1 },
  rowValue: { fontFamily: fonts.text700, fontSize: 15, color: c.ink },
  rowStrongLabel: { fontFamily: fonts.text800, fontSize: 16, color: c.ink },
  rowStrong: { fontFamily: fonts.display700, fontSize: 20, color: c.ink },
  divider: { height: 1, backgroundColor: c.border },
}));
