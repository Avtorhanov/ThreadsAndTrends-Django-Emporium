import { useEffect } from "react";
import { ActivityIndicator, StyleSheet } from "react-native";
import Animated, {
  interpolateColor,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";

import { fonts } from "../theme/fonts";
import { ease, motion, REDUCED_FADE_MS } from "../theme/motion";
import { makeStyles, useTheme } from "../theme/ThemeProvider";
import { radius, size } from "../theme/tokens";
import { PressScale } from "./ui";

type Props = {
  title: string;
  doneTitle: string;
  /** Действие выполнено: кнопка заливается слева направо (motion.ctaFill, 550 мс). */
  done: boolean;
  trailing?: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
};

/** Главная кнопка карточки товара («В корзину»): высота 62, цена справа, заливка при успехе. */
export function FillButton({ title, doneTitle, done, trailing, onPress, disabled, loading }: Props) {
  const s = useStyles();
  const { c } = useTheme();
  const reduced = useReducedMotion();
  const progress = useSharedValue(done ? 1 : 0);

  useEffect(() => {
    const duration = reduced ? REDUCED_FADE_MS : motion.ctaFill.ms;
    progress.value = withTiming(done ? 1 : 0, { duration: done ? duration : REDUCED_FADE_MS, easing: ease.out });
  }, [done, reduced, progress]);

  const fill = useAnimatedStyle(() =>
    reduced ? { opacity: progress.value } : { transform: [{ scaleX: progress.value }] },
  );
  const ink = useAnimatedStyle(() => ({
    color: interpolateColor(progress.value, [0, 1], [c.ctaInk, c.ctaDoneInk]),
  }));

  return (
    <PressScale
      accessibilityRole="button"
      accessibilityState={{ disabled: Boolean(disabled || loading), busy: Boolean(loading) }}
      accessibilityLabel={trailing ? `${done ? doneTitle : title}, ${trailing}` : done ? doneTitle : title}
      onPress={onPress}
      disabled={disabled || loading}
      scale={0.98}
      style={[s.button, (disabled || loading) && !done && s.dimmed]}
    >
      <Animated.View pointerEvents="none" style={[s.fill, fill]} />
      {loading ? (
        <ActivityIndicator color={c.ctaInk} />
      ) : (
        <>
          <Animated.Text style={[s.text, ink]}>{done ? doneTitle : title}</Animated.Text>
          {trailing ? <Animated.Text style={[s.trailing, ink]}>{trailing}</Animated.Text> : null}
        </>
      )}
    </PressScale>
  );
}

const useStyles = makeStyles(({ c }) => ({
  button: {
    height: size.ctaHeight,
    borderRadius: radius.cta,
    paddingHorizontal: 24,
    backgroundColor: c.ctaBg,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    overflow: "hidden",
    boxShadow: "0 20px 32px -14px rgba(0,0,0,.6)",
  },
  dimmed: { opacity: 0.55 },
  fill: { ...StyleSheet.absoluteFillObject, backgroundColor: c.ctaFill, transformOrigin: "left" },
  text: { fontFamily: fonts.text800, fontSize: 16 },
  trailing: { fontFamily: fonts.display700, fontSize: 15 },
}));
