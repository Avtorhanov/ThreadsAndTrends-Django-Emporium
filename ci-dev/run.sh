#!/usr/bin/env bash
# Шаг 2: чистка зависимостей, typecheck, сборка веб-версии.
set -uo pipefail
OUT="$PWD/ci-dev/out"
python3 scripts/gen_tokens.py --check > "$OUT/tokens.txt" 2>&1; echo "tokens exit=$?" >> "$OUT/tokens.txt"
cd mobile
npm ci --no-audit --no-fund > "$OUT/npm.txt" 2>&1
npm uninstall --no-audit --no-fund @react-native-masked-view/masked-view expo-navigation-bar >> "$OUT/npm.txt" 2>&1
npx expo install --fix >> "$OUT/npm.txt" 2>&1
cp package.json package-lock.json "$OUT/"
npm run typecheck > "$OUT/typecheck.txt" 2>&1; echo "typecheck exit=$?" >> "$OUT/typecheck.txt"
EXPO_NO_TELEMETRY=1 npx expo export --platform web --output-dir /tmp/web > "$OUT/export.txt" 2>&1; echo "export exit=$?" >> "$OUT/export.txt"
tail -n 40 "$OUT/export.txt" > "$OUT/export-tail.txt"
grep -n "import { [^}]*} from \"react-native-reanimated\"" -r ../mobile/app ../mobile/src > /dev/null
grep -o "export { [^}]*}" node_modules/react-native-reanimated/lib/typescript/index.d.ts | tr ',' '\n' | grep -ci "runOnJS" > "$OUT/reanimated-runonjs.txt" || true
