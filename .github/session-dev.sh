#!/usr/bin/env bash
# Шаги временного workflow session-dev. Каждая проверка пишет вывод и код выхода в /tmp/report.
set +e
R=/tmp/report
mkdir -p $R
echo "${GITHUB_SHA}" > $R/sha.txt
step() { name=$1; shift; "$@" > $R/$name.txt 2>&1; echo "exit=$?" >> $R/$name.txt; }

# --- Зависимости, которых нет в среде разработки ---
pip index versions sentry-sdk > $R/pip-versions.txt 2>&1
if ! grep -q '"react-native-web"' mobile/package.json; then
  (cd mobile && npm ci --no-audit --no-fund && npx expo install react-dom react-native-web @expo/metro-runtime) > $R/expo-install.txt 2>&1
  echo "exit=$?" >> $R/expo-install.txt
fi

# --- Фото демо-каталога ---
step fetch-images python scripts/fetch_demo_images.py

# --- Автоисправления ---
ruff check --fix . > $R/ruff.txt 2>&1; echo "check exit=$?" >> $R/ruff.txt
ruff format . >> $R/ruff.txt 2>&1
ruff check . >> $R/ruff.txt 2>&1; echo "recheck exit=$?" >> $R/ruff.txt
step migrations python manage.py makemigrations --check --dry-run -v 3
python manage.py spectacular --file openapi/schema.yml > $R/schema.txt 2>&1
step schema-validate python manage.py spectacular --validate --fail-on-warn --file openapi/schema.yml

# --- Проверки ---
step pytest pytest -q -p no:cacheprovider --tb=short -rfE
for app in mobile admin-panel; do
  (cd $app && npm ci --no-audit --no-fund > $R/npm-$app.txt 2>&1)
  (cd $app && npm run typecheck) > $R/typecheck-$app.txt 2>&1; echo "exit=$?" >> $R/typecheck-$app.txt
done
(cd admin-panel && npx vite build) > $R/build-admin-panel.txt 2>&1; echo "exit=$?" >> $R/build-admin-panel.txt
(cd mobile && npx expo export --platform web --output-dir /tmp/shop-dist) > $R/build-shop.txt 2>&1; echo "exit=$?" >> $R/build-shop.txt
DJANGO_SETTINGS_MODULE=myshop.settings.prod SECRET_KEY=ci-deploy-check-not-a-real-secret-key-0123456789-abcdefgh ALLOWED_HOSTS=example.com \
  python manage.py check --deploy --fail-level WARNING > $R/deploy-check.txt 2>&1; echo "exit=$?" >> $R/deploy-check.txt

# --- E2E прод-стека (если есть) ---
if [ -f deploy/e2e.sh ]; then
  step e2e bash deploy/e2e.sh $R
fi

git status --short > $R/changed.txt
exit 0
