import {
  Manrope_500Medium,
  Manrope_600SemiBold,
  Manrope_700Bold,
  Manrope_800ExtraBold,
} from "@expo-google-fonts/manrope";
import { Unbounded_500Medium, Unbounded_700Bold } from "@expo-google-fonts/unbounded";

/** Файлы шрифтов для useFonts. Веса — из tokens.json (font.display / font.text). */
export const fontAssets = {
  Unbounded_500Medium,
  Unbounded_700Bold,
  Manrope_500Medium,
  Manrope_600SemiBold,
  Manrope_700Bold,
  Manrope_800ExtraBold,
};

// В React Native у каждого начертания своё имя семейства: fontWeight на Android не выбирает файл.
export const fonts = {
  display500: "Unbounded_500Medium",
  display700: "Unbounded_700Bold",
  text500: "Manrope_500Medium",
  text600: "Manrope_600SemiBold",
  text700: "Manrope_700Bold",
  text800: "Manrope_800ExtraBold",
} as const;
