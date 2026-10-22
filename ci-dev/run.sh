#!/usr/bin/env bash
# Шаг 3: typecheck, иконки, e2e прод-стека со скриншотами обеих тем.
set -uo pipefail
ROOT="$PWD"
OUT="$ROOT/ci-dev/out"
cd mobile
npm ci --no-audit --no-fund > "$OUT/npm.txt" 2>&1
npm run typecheck > "$OUT/typecheck.txt" 2>&1; tc=$?; echo "typecheck exit=$tc" >> "$OUT/typecheck.txt"
cd "$ROOT"
pip install -q pillow > /dev/null 2>&1
python3 scripts/make_icons.py > "$OUT/icons.txt" 2>&1
mkdir -p "$OUT/icons" && cp mobile/assets/*.png mobile/public/icons/*.png "$OUT/icons/"
[ "$tc" = 0 ] || exit 1
git config user.name ci && git config user.email ci@example.com
bash deploy/e2e.sh "$OUT/e2e" > "$OUT/e2e.txt" 2>&1; echo "e2e exit=$?" >> "$OUT/e2e.txt"
docker compose -f compose.prod.yml logs --no-color --tail 80 > "$OUT/compose-logs.txt" 2>&1 || true
