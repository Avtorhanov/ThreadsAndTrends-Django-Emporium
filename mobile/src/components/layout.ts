import { useWindowDimensions } from "react-native";

/** Ширина колонки контента: в браузере приложение не растягивается шире MAX_CONTENT_WIDTH. */
export const MAX_CONTENT_WIDTH = 1200;

export function useContentWidth(): number {
  const { width } = useWindowDimensions();
  return Math.min(width, MAX_CONTENT_WIDTH);
}

/** Колонок в сетке товаров: телефон — 2, планшет — 3, широкий экран — 4. */
export function useGridColumns(): number {
  const width = useContentWidth();
  if (width >= 960) return 4;
  if (width >= 640) return 3;
  return 2;
}
