#!/bin/sh
set -e

# Прод (compose.prod.yml, сервис app запускается от root): тома фото и статики должны
# принадлежать пользователю app — даже если том создан другим контейнером или файлы
# восстановлены из бэкапа от root. Затем процесс перезапускается от app (средствами Python —
# он в образе есть всегда, в отличие от setpriv/gosu).
if [ "$(id -u)" = "0" ]; then
    for dir in /data/media ${STATIC_EXPORT_DIR:-}; do
        [ -d "$dir" ] && find "$dir" ! -user app -exec chown app:app {} +
    done
    exec python -c '
import os, pwd, sys
user = pwd.getpwnam("app")
os.setgroups([])
os.setgid(user.pw_gid)
os.setuid(user.pw_uid)
os.environ["HOME"] = user.pw_dir
os.execvp(sys.argv[1], sys.argv[1:])
' "$0" "$@"
fi

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
    python manage.py seed_demo || echo "seed_demo пропущен (причина — выше)"
fi

# Уменьшенные копии фото для витрины — только у фото без копий (загруженных до сессии 9 или
# пока воркер не успел); новые фото обрабатывает воркер.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py make_thumbnails || echo "make_thumbnails пропущен (причина — выше)"
fi

# Прод: статика Django (админка, витрина, Swagger) копируется в общий том, её раздаёт Caddy.
if [ -n "${STATIC_EXPORT_DIR:-}" ]; then
    cp -a /app/staticfiles/. "${STATIC_EXPORT_DIR}/"
fi

exec "$@"
