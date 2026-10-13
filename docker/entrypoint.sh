#!/bin/sh
set -e

# Миграции выполняет только сервис web (RUN_MIGRATIONS=1); worker и scheduler
# стартуют после того, как web стал healthy.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py createcachetable
fi

# Демо-каталог для локальной разработки. loaddata идемпотентен (фиксированные pk).
if [ "${LOAD_FIXTURES:-0}" = "1" ]; then
    python manage.py loaddata fixtures/catalog.json
fi

exec "$@"
