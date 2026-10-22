import { createContext, type ReactNode, useContext } from "react";
import {
  interpolate,
  type SharedValue,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
} from "react-native-reanimated";

import { motion } from "../theme/motion";

/**
 * Глубина под листом товара: 0 — каталог на месте, 1 — открыт лист (каталог уменьшен до .93
 * и бледнее, motion.listBehind). Значение двигает экран товара, применяют вкладки.
 */
const SheetDepthContext = createContext<SharedValue<number> | null>(null);

export function SheetDepthProvider({ children }: { children: ReactNode }) {
  const depth = useSharedValue(0);
  return <SheetDepthContext.Provider value={depth}>{children}</SheetDepthContext.Provider>;
}

export function useSheetDepth(): SharedValue<number> {
  const depth = useContext(SheetDepthContext);
  if (!depth) throw new Error("useSheetDepth вне SheetDepthProvider");
  return depth;
}

/** Стиль экрана позади листа. Размытие не используется: на Android оно дорогое. */
export function useBehindStyle() {
  const depth = useSheetDepth();
  const reduced = useReducedMotion();
  const { scale, opacity } = motion.listBehind;
  return useAnimatedStyle(() => ({
    opacity: interpolate(depth.value, [0, 1], [1, opacity]),
    transform: reduced
      ? []
      : [
          { scale: interpolate(depth.value, [0, 1], [1, scale]) },
          { translateY: interpolate(depth.value, [0, 1], [0, -6]) },
        ],
  }));
}
