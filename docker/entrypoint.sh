#!/bin/sh
set -e

# Миграции выполняет только основной сервис (RUN_MIGRATIONS=1); worker и scheduler
# стартуют после того, как он стал healthy.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py createcachetable
fi

# Администратор из ADMIN_EMAIL/ADMIN_PASSWORD (создаётся один раз, пароль потом не трогается).
if [ "${ENSURE_ADMIN:-0}" = "1" ]; then
    python manage.py ensure_admin
fi

# Демо-каталог с фото. Идемпотентно; если в каталоге уже есть свои товары — пропускается.
if [ "${LOAD_FIXTURES:-0}" = "1" ]; then
    python manage.py seed_demo || echo "seed_demo пропущен"
fi

# Прод: статика Django (админка, Swagger) копируется в общий том, её раздаёт Caddy.
if [ -n "${STATIC_EXPORT_DIR:-}" ]; then
    cp -a /app/staticfiles/. "${STATIC_EXPORT_DIR}/"
fi

exec "$@"
