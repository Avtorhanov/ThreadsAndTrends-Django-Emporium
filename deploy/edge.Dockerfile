# Образ Caddy с собранной панелью администратора (React + Vite). Витрина — Django (app),
# её статика — общий том. Контекст — корень репозитория (deploy/edge.Dockerfile.dockerignore).

FROM node:22-slim AS panel
WORKDIR /src
COPY openapi/ openapi/
COPY admin-panel/package.json admin-panel/package-lock.json admin-panel/.npmrc admin-panel/
RUN cd admin-panel && npm ci --no-audit --no-fund
COPY admin-panel/ admin-panel/
RUN cd admin-panel && npm run build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=panel /src/admin-panel/dist /srv/panel
