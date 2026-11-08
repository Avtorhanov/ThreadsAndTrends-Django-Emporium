# Бэкап: pg_dump той же версии, что база, и rclone для копии в Google Диск.
FROM postgres:16-alpine
RUN apk add --no-cache rclone
