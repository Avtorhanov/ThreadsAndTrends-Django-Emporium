#!/bin/sh
# Бэкап БД (pg_dump, формат custom) и фото товаров в /backups (на сервере — ./backups),
# затем шифрованная копия в Google Диск, если заданы BACKUP_GDRIVE_TOKEN и BACKUP_PASSPHRASE.
# Запускается по расписанию в сервисе backup (BACKUP_CRON) и вручную: ./deploy.sh backup
#   backup.sh                 — сделать копию
#   backup.sh fetch [файл]    — скачать копию с Диска в /backups/drive (по умолчанию последнюю)
set -eu
dir=/backups
keep=${BACKUP_KEEP_DAYS:-14}
remote_keep=${BACKUP_REMOTE_KEEP_DAYS:-30}

# rclone шифрует содержимое и имена файлов сам; ключ — только BACKUP_PASSPHRASE.
remote_setup() {
  [ -n "${BACKUP_PASSPHRASE:-}" ] || { echo "Задайте BACKUP_PASSPHRASE в .env" >&2; exit 1; }
  export RCLONE_CONFIG_GDRIVE_TYPE=drive RCLONE_CONFIG_GDRIVE_SCOPE=drive.file
  export RCLONE_CONFIG_GDRIVE_TOKEN="$BACKUP_GDRIVE_TOKEN"
  export RCLONE_CONFIG_SECRET_TYPE=crypt
  export RCLONE_CONFIG_SECRET_REMOTE="gdrive:${BACKUP_GDRIVE_FOLDER:-didi-shop-backup}"
  RCLONE_CONFIG_SECRET_PASSWORD=$(rclone obscure "$BACKUP_PASSPHRASE")
  export RCLONE_CONFIG_SECRET_PASSWORD
  # Удалённое — сразу, а не в корзину: корзина занимает те же 15 ГБ Диска.
  export RCLONE_DRIVE_USE_TRASH=false
}

fetch() {
  [ -n "${BACKUP_GDRIVE_TOKEN:-}" ] || { echo "Копия в Google Диск не настроена" >&2; exit 1; }
  remote_setup
  name=${1:-$(rclone lsf secret:db | sort | tail -n 1)}
  [ -n "$name" ] || { echo "На Диске нет копий" >&2; exit 1; }
  rm -rf "$dir/drive"
  mkdir -p "$dir/drive/media"
  rclone copy "secret:db/$name" "$dir/drive"
  rclone copy secret:media "$dir/drive/media"
  tar -C "$dir/drive/media" -czf "$dir/drive/media.tar.gz" .
  rm -rf "$dir/drive/media"
  echo "Скачано: $dir/drive/$name и $dir/drive/media.tar.gz"
}

if [ "${1:-}" = "fetch" ]; then
  shift
  fetch "$@"
  exit 0
fi

ts=$(date -u +%Y%m%d-%H%M%S)
mkdir -p "$dir"

# Первая попытка: от неё мониторинг считает срок, пока нет меток .ok-local / .ok-remote.
[ -f "$dir/.first-run" ] || touch "$dir/.first-run"

# Сначала во временный файл: неполный бэкап никогда не выглядит готовым.
# Каждая команда — отдельной строкой: в списке «a && b» сбой «a» не останавливает скрипт при set -e.
tmp_db="$dir/.db-$ts.dump"
tmp_media="$dir/.media-$ts.tar.gz"
trap 'rm -f "$tmp_db" "$tmp_media"' EXIT
# Остатки прерванных запусков (отключение питания): trap их не убрал.
find "$dir" -maxdepth 1 \( -name '.db-*.dump' -o -name '.media-*.tar.gz' \) -mmin +120 -delete

pg_dump --format=custom --no-owner --file="$tmp_db"
[ -s "$tmp_db" ] || { echo "Бэкап не сделан: дамп базы пуст" >&2; exit 1; }
mv "$tmp_db" "$dir/db-$ts.dump"
tar -C /media -czf "$tmp_media" .
mv "$tmp_media" "$dir/media-$ts.tar.gz"

find "$dir" -maxdepth 1 \( -name 'db-*.dump' -o -name 'media-*.tar.gz' \) -mtime +"$keep" -delete
touch "$dir/.ok-local"
echo "Бэкап готов: db-$ts.dump, media-$ts.tar.gz ($(du -sh "$dir" | cut -f1) в $dir, хранится $keep дн.)"

if [ -n "${BACKUP_GDRIVE_TOKEN:-}" ]; then
  remote_setup
  rclone copy "$dir/db-$ts.dump" secret:db
  # Фото не меняются: уходят только новые файлы, а не архив целиком каждый день.
  rclone copy /media secret:media
  # Старое удаляем только после успешной отправки: при сбое set -e остановит скрипт раньше.
  rclone delete secret:db --min-age "${remote_keep}d"
  touch "$dir/.ok-remote"
  echo "Копия в Google Диск отправлена, база хранится там $remote_keep дн."
fi
