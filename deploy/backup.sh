#!/bin/sh
# Бэкап БД (pg_dump, формат custom) и фото товаров в /backups (на сервере — ./backups).
# Запускается по расписанию в сервисе backup (BACKUP_CRON) и вручную: ./deploy.sh backup
set -eu
ts=$(date -u +%Y%m%d-%H%M%S)
dir=/backups
keep=${BACKUP_KEEP_DAYS:-14}
mkdir -p "$dir"

# Сначала во временный файл: неполный бэкап никогда не выглядит готовым.
pg_dump --format=custom --no-owner --file="$dir/.db-$ts.dump" && mv "$dir/.db-$ts.dump" "$dir/db-$ts.dump"
tar -C /media -czf "$dir/.media-$ts.tar.gz" . && mv "$dir/.media-$ts.tar.gz" "$dir/media-$ts.tar.gz"

find "$dir" -maxdepth 1 \( -name 'db-*.dump' -o -name 'media-*.tar.gz' \) -mtime +"$keep" -delete
echo "Бэкап готов: db-$ts.dump, media-$ts.tar.gz ($(du -sh "$dir" | cut -f1) в $dir, хранится $keep дн.)"
