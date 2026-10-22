import { Easing } from "react-native-reanimated";

import { easing as curves, motion } from "./tokens";

const bezier = ([x1, y1, x2, y2]: readonly [number, number, number, number]) => Easing.bezier(x1, y1, x2, y2);

/** Кривые и длительности «Лайм-тек» (tokens.json → motion). */
export const ease = {
  out: bezier(curves.easeOut),
  soft: bezier(curves.easeSoft),
  tab: bezier(curves.easeTab),
};

export { motion };

/** «Уменьшить движение»: переходы заменяются коротким fade без масштаба и размытия. */
export const REDUCED_FADE_MS = 150;
