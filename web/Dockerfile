FROM node:20-alpine AS builder

WORKDIR /app

RUN corepack enable pnpm

COPY web/package.json web/pnpm-lock.yaml* web/pnpm-workspace.yaml* web/.npmrc* ./
RUN pnpm approve-builds esbuild || (pnpm install; pnpm approve-builds esbuild)

COPY web ./
RUN pnpm build

FROM caddy:2-alpine AS runtime

COPY --from=builder /app/dist /usr/share/caddy
COPY web/Caddyfile /etc/caddy/Caddyfile

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:80/ || exit 1
