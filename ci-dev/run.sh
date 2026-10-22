#!/usr/bin/env bash
# Шаг 1: установка зависимостей «Лайм-тек» и разведка типов.
set -euo pipefail
OUT="$PWD/ci-dev/out"
cd mobile
npm ci --no-audit --no-fund
npx expo install react-native-reanimated react-native-worklets expo-blur expo-linear-gradient \
  @react-native-masked-view/masked-view expo-font @expo-google-fonts/unbounded \
  @expo-google-fonts/manrope expo-system-ui expo-navigation-bar expo-splash-screen react-native-svg
cp package.json package-lock.json app.json "$OUT/"
npx expo install --check > "$OUT/expo-check.txt" 2>&1 || true

{
  echo "== versions"
  for p in react-native react-native-web react-native-reanimated react-native-worklets expo-blur \
    expo-linear-gradient @react-native-masked-view/masked-view expo-router expo-splash-screen \
    expo-navigation-bar expo-system-ui react-native-svg expo-font; do
    printf '%s %s\n' "$p" "$(node -p "require('$p/package.json').version")"
  done
  echo "== RN style types: boxShadow / backgroundImage / filter"
  grep -rn "boxShadow\|backgroundImage\|filter?:" node_modules/react-native/Libraries/StyleSheet/StyleSheetTypes.d.ts | head -20
  echo "== RNW boxShadow / backgroundImage / backdropFilter"
  grep -rln "boxShadow" node_modules/react-native-web/dist/exports/StyleSheet | head
  grep -rn "backdropFilter\|backgroundImage" node_modules/react-native-web/dist/exports/StyleSheet/*.js | head
  echo "== reanimated exports"
  grep -o "export { [^}]*}" node_modules/react-native-reanimated/lib/typescript/index.d.ts | tr ',' '\n' | grep -i "scroll\|ReduceMotion\|interpolateColor\|withTiming\|FadeIn\|SlideIn\|Easing\|useReducedMotion\|LinearTransition\|Keyframe" | head -40
  echo "== expo-blur props"
  sed -n 1,80p node_modules/expo-blur/build/BlurView.types.d.ts
  echo "== expo-navigation-bar"
  grep -n "export declare function" node_modules/expo-navigation-bar/build/*.d.ts | head -20
  echo "== expo-system-ui"
  grep -n "export declare function" node_modules/expo-system-ui/build/*.d.ts | head
  echo "== expo-router Tabs / BottomTabBarProps"
  ls node_modules/expo-router/build/layouts/ | head -30
  grep -rn "BottomTabBarProps" node_modules/expo-router/build/layouts/*.d.ts | head
  grep -rln "export type BottomTabBarProps" node_modules/@react-navigation/bottom-tabs/lib/typescript 2>/dev/null | head -3
  echo "== app.json newArch"
  grep -n "newArch" app.json || echo "(нет ключа — по умолчанию в SDK 57 новая архитектура)"
} > "$OUT/recon.txt" 2>&1
