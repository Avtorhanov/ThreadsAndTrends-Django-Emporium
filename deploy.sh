#!/usr/bin/env bash
# DiDi-shop: запуск и обновление на сервере одной командой.
#
#   sudo ./deploy.sh              — первый запуск и каждое обновление (после git pull)
#   sudo ./deploy.sh status       — состояние сервисов
#   sudo ./deploy.sh logs [сервис] — логи (app, worker, scheduler, caddy, db, backup)
#   sudo ./deploy.sh backup       — бэкап прямо сейчас (в ./backups)
#   sudo ./deploy.sh restore backups/db-….dump [backups/media-….tar.gz] — восстановление
#   sudo ./deploy.sh smoke        — нагрузочный smoke-тест оформления заказа
#
# Сервер: Ubuntu 22.04/24.04 или Debian 12, от 2 ГБ RAM. Docker ставится автоматически.
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE=(docker compose -f compose.prod.yml)
ENV_FILE=.env

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!   %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mОшибка: %s\033[0m\n' "$*" >&2; exit 1; }

# Значение из .env (последняя запись, без кавычек). .env не исполняется как shell-скрипт.
env_get() {
  local line
  line=$(grep -E "^$1=" "$ENV_FILE" | tail -n 1 || true)
  line=${line#*=}
  line=${line%\"}; line=${line#\"}; line=${line%\'}; line=${line#\'}
  printf '%s' "$line"
}

env_set() {
  if grep -qE "^$1=" "$ENV_FILE"; then
    # Разделитель | — в сгенерированных значениях его нет.
    sed -i.bak "s|^$1=.*|$1=$2|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
  else
    printf '%s=%s\n' "$1" "$2" >> "$ENV_FILE"
  fi
}

# `|| true`: head закрывает канал раньше tr (SIGPIPE), что при pipefail считается ошибкой.
random_secret() { (LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c "$1") || true; }

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    [ "$(id -u)" -eq 0 ] || die "Docker не установлен. Запустите от root: sudo ./deploy.sh"
    say "Устанавливаю Docker"
    curl -fsSL https://get.docker.com | sh
  fi
  docker info >/dev/null 2>&1 || die "Нет доступа к Docker. Запустите от root: sudo ./deploy.sh"
  docker compose version >/dev/null 2>&1 || die "Нужен Docker Compose v2 (docker compose)."
}

public_ip() {
  curl -fsS -4 --max-time 5 https://api.ipify.org 2>/dev/null \
    || curl -fsS -4 --max-time 5 https://ifconfig.me 2>/dev/null \
    || true
}

GENERATED_ADMIN_PASSWORD=""

ensure_env() {
  if [ ! -f "$ENV_FILE" ]; then
    cp .env.prod.example "$ENV_FILE"
    echo "Создан файл .env из .env.prod.example."
  fi
  chmod 600 "$ENV_FILE"

  # Адрес сайта. Без своего домена — бесплатное имя <IP>.sslip.io: HTTPS-сертификат
  # выпускается так же, домен подключается позже (DOMAIN в .env + ./deploy.sh).
  local domain
  domain=$(env_get DOMAIN)
  if [ -z "$domain" ]; then
    local ip
    ip=$(public_ip)
    [ -n "$ip" ] || die "Не удалось определить внешний IP сервера. Укажите DOMAIN в .env."
    domain="${ip//./-}.sslip.io"
    env_set DOMAIN "$domain"
    echo "Свой домен не задан — магазин будет работать по адресу https://$domain"
  fi
  case "$domain" in
    http://* | https://* | */* | *" "* | *,*) die "DOMAIN — только имя домена, без https:// и слэшей: $domain" ;;
  esac

  local admin_email
  admin_email=$(env_get ADMIN_EMAIL)
  if [ -z "$admin_email" ] && [ -t 0 ]; then
    read -r -p "Email администратора магазина (для входа в панель): " admin_email
    [ -z "$admin_email" ] || env_set ADMIN_EMAIL "$admin_email"
  fi
  case "$admin_email" in
    *@*.*) ;;
    *) die "В .env не задан ADMIN_EMAIL (email администратора): nano .env" ;;
  esac
  if [ -z "$(env_get ADMIN_PASSWORD)" ]; then
    GENERATED_ADMIN_PASSWORD="Dd$(random_secret 14)"
    env_set ADMIN_PASSWORD "$GENERATED_ADMIN_PASSWORD"
  fi
  local admin_password
  admin_password=$(env_get ADMIN_PASSWORD)
  [ ${#admin_password} -ge 8 ] || die "ADMIN_PASSWORD в .env должен быть не короче 8 символов."

  if [ -z "$(env_get SECRET_KEY)" ]; then
    env_set SECRET_KEY "$(random_secret 64)"
    echo "SECRET_KEY сгенерирован."
  fi
  if [ -z "$(env_get DB_PASSWORD)" ]; then
    env_set DB_PASSWORD "$(random_secret 32)"
    echo "DB_PASSWORD сгенерирован."
  fi
  if [ "$(env_get ORDERS_ONLINE_PAYMENT_ENABLED)" = "True" ] && \
     { [ -z "$(env_get YOOKASSA_SHOP_ID)" ] || [ -z "$(env_get YOOKASSA_SECRET_KEY)" ]; }; then
    die "ORDERS_ONLINE_PAYMENT_ENABLED=True, но не заданы YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY."
  fi

  # Прежний адрес (например, sslip.io до покупки домена) продолжает работать: он зашит
  # в уже установленные APK. Список — EXTRA_DOMAINS в .env (ненужный адрес можно удалить).
  local previous extra
  previous=$(cat .deployed-domain 2>/dev/null || true)
  extra=$(env_get EXTRA_DOMAINS | tr -d ' ')
  if [ -n "$previous" ] && [ "$previous" != "$domain" ] && [ "$previous" != "localhost" ]; then
    case ",$extra," in
      *",$previous,"*) ;;
      *)
        extra="${extra:+$extra,}$previous"
        env_set EXTRA_DOMAINS "$extra"
        warn "Адрес сменился: $previous → $domain. Старый адрес тоже продолжит работать (EXTRA_DOMAINS)."
        warn "Соберите новый APK с адресом https://$domain (docs/LAUNCH.md, шаг «Android»)."
        ;;
    esac
  fi
  local sites="$domain" prefixes="https://$domain/" host
  for host in ${extra//,/ }; do
    [ "$host" = "$domain" ] && continue
    sites="$sites, $host"
    prefixes="$prefixes,https://$host/"
  done
  env_set SITE_HOSTS "$sites"
  env_set RETURN_URL_PREFIXES "$prefixes"
}

ensure_swap() {
  # Сборка веб-версии приложения требует ~1.5 ГБ памяти: на маленьких VPS добавляем swap.
  [ "$(uname -s)" = "Linux" ] && [ "$(id -u)" -eq 0 ] || return 0
  local mem_kb swap_kb
  mem_kb=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
  swap_kb=$(awk '/SwapTotal/ {print $2}' /proc/meminfo)
  if [ "$mem_kb" -lt 3500000 ] && [ "$swap_kb" -lt 1000000 ] && [ ! -e /swapfile ]; then
    say "Памяти меньше 4 ГБ — добавляю swap 2 ГБ"
    fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
}

check_dns() {
  local domain=$1 server_ip domain_ips
  [ "$domain" = "localhost" ] && return 0
  server_ip=$(curl -fsS -4 --max-time 5 https://api.ipify.org 2>/dev/null || true)
  domain_ips=$(getent ahostsv4 "$domain" 2>/dev/null | awk '{print $1}' | sort -u | tr '\n' ' ' || true)
  if [ -z "$domain_ips" ]; then
    warn "Домен $domain пока не находится в DNS. HTTPS-сертификат выпустится, когда A-запись заработает"
    warn "(обычно от 15 минут до нескольких часов). Сайт подхватит его сам, повторять деплой не нужно."
  elif [ -n "$server_ip" ] && ! grep -qw "$server_ip" <<<"$domain_ips"; then
    warn "Домен $domain указывает на $domain_ips, а IP этого сервера — $server_ip."
    warn "Исправьте A-запись у регистратора, иначе HTTPS-сертификат не выпустится."
  fi
}

open_firewall() {
  if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
    ufw allow OpenSSH >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; ufw allow 443/udp >/dev/null
  fi
}

deploy() {
  ensure_docker
  ensure_env
  local domain
  domain=$(env_get DOMAIN)
  ensure_swap
  check_dns "$domain"
  open_firewall
  mkdir -p backups

  say "Сборка и запуск (первый раз — 5–15 минут)"
  "${COMPOSE[@]}" build
  "${COMPOSE[@]}" up -d --remove-orphans --wait --wait-timeout 600 \
    || { "${COMPOSE[@]}" ps; "${COMPOSE[@]}" logs --tail 80 app; die "Сервисы не запустились (логи выше)."; }
  docker image prune -f >/dev/null 2>&1 || true
  printf '%s\n' "$domain" > .deployed-domain

  say "Проверка"
  local https_opts=(-fsS --max-time 20 --resolve "$domain:443:127.0.0.1")
  [ "$domain" = "localhost" ] && https_opts+=(-k)
  if curl "${https_opts[@]}" "https://$domain/api/v1/health/" >/dev/null 2>&1; then
    echo "HTTPS работает."
  else
    warn "https://$domain пока не отвечает — Caddy ещё получает сертификат (нужна работающая A-запись)."
    warn "Проверьте позже: ./deploy.sh logs caddy"
  fi

  cat <<EOF

Готово.
  Магазин (веб-версия приложения): https://$domain/
  Панель администратора:           https://$domain/panel/   (вход: $(env_get ADMIN_EMAIL))
  Резервная админка Django:        https://$domain/admin/
  Webhook для ЮKassa:              https://$domain/api/v1/payments/webhook/yookassa/
  Бэкапы:                          $(pwd)/backups (ежедневно)
EOF
  if [ -n "$GENERATED_ADMIN_PASSWORD" ]; then
    printf '\n  Пароль администратора: %s\n  (сохранён в .env как ADMIN_PASSWORD; после входа смените его в панели)\n' \
      "$GENERATED_ADMIN_PASSWORD"
  fi
}

restore() {
  local db_dump=${1:-} media_tar=${2:-}
  [ -f "$db_dump" ] || die "Укажите файл бэкапа БД: ./deploy.sh restore backups/db-….dump [backups/media-….tar.gz]"
  [ -z "$media_tar" ] || [ -f "$media_tar" ] || die "Файл $media_tar не найден."
  read -r -p "Текущие данные будут заменены данными из бэкапа. Продолжить? [y/N] " answer
  [ "$answer" = "y" ] || [ "$answer" = "Y" ] || die "Отменено."
  restore_noninteractive "$db_dump" "$media_tar"
}

restore_noninteractive() {
  local db_dump=$1 media_tar=${2:-}
  say "Останавливаю приложение"
  "${COMPOSE[@]}" stop caddy app worker scheduler
  say "Восстанавливаю БД из $db_dump"
  "${COMPOSE[@]}" exec -T db pg_restore --clean --if-exists --no-owner -U didi -d didi < "$db_dump" \
    || warn "pg_restore сообщил об ошибках (см. выше) — проверьте данные после запуска."
  if [ -n "$media_tar" ]; then
    say "Восстанавливаю фото из $media_tar"
    "${COMPOSE[@]}" run --rm --no-deps -T --entrypoint sh app \
      -c 'find /data/media -mindepth 1 -delete && tar -C /data/media -xzf -' < "$media_tar"
  fi
  say "Запускаю приложение"
  "${COMPOSE[@]}" up -d --wait --wait-timeout 300
  echo "Восстановлено."
}

case "${1:-deploy}" in
  deploy) deploy ;;
  status) "${COMPOSE[@]}" ps ;;
  logs) shift; "${COMPOSE[@]}" logs -f --tail 200 "$@" ;;
  backup) "${COMPOSE[@]}" exec backup sh /usr/local/bin/backup.sh ;;
  restore) shift; restore "$@" ;;
  restore-yes) shift; restore_noninteractive "$@" ;;
  smoke) shift; python3 deploy/smoke_checkout.py "https://$(env_get DOMAIN)" "$@" ;;
  *) sed -n '2,12p' "$0"; exit 1 ;;
esac
