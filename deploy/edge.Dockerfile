# Образ Caddy с собранными клиентами: витрина (веб-версия мобильного приложения, Expo web)
# и панель администратора. Контекст — корень репозитория (deploy/edge.Dockerfile.dockerignore).

FROM node:22-slim AS panel
WORKDIR /src
COPY openapi/ openapi/
COPY admin-panel/package.json admin-panel/package-lock.json admin-panel/.npmrc admin-panel/
RUN cd admin-panel && npm ci --no-audit --no-fund
COPY admin-panel/ admin-panel/
RUN cd admin-panel && npm run build

FROM node:22-slim AS shop
WORKDIR /src
COPY openapi/ openapi/
COPY mobile/package.json mobile/package-lock.json mobile/.npmrc mobile/
RUN cd mobile && npm ci --no-audit --no-fund
COPY mobile/ mobile/
# API — тот же домен (относительные адреса), поэтому EXPO_PUBLIC_API_URL пустой.
ENV EXPO_PUBLIC_API_URL="" \
    NODE_OPTIONS=--max-old-space-size=1536
RUN cd mobile && npm run gen:api && npx expo export --platform web --output-dir /out

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=panel /src/admin-panel/dist /srv/panel
COPY --from=shop /out /srv/shop
