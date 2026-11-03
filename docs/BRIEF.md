# Project Brief: Personal AI-Curated Video Web App (`mytube`)

> **Document Status**: Canonical Project Requirements Document (PRD) and Agent Brief.
> Requirement IDs (`FR-xx`, `NFR-xx`, `SEC-xx`) are stable and referenced in tests, commits, and PRs.
> Infrastructure patterns (Cloudflare, Redis, PostgreSQL) align with `~/Documents/aml/chatapp/docker-compose.yml`.
> Host port allocations strictly avoid all conflicting ports (`WEB_PORT=3005`, `API_PORT=8005`, `POSTGRES_PORT=5436`, `REDIS_PORT=6381`, `MOCK_OIDC_PORT=8087`).

---

## 0. Role and Goal

You are a senior full-stack engineer, a security engineer, and a QA lead. Build a complete, production-quality, **self-hosted personal video web app** that works like a minimal YouTube. Users sign in with Google, pick interest categories, browse a dashboard of videos grouped by category, and create **AI-curated channels**. Each channel is defined by a natural-language prompt, and an LLM uses it to discover, pre-filter, rank, and categorize videos for that channel. Users can like, share, and save videos, and organize them into playlists.

- **App Name**: `mytube` (configurable via `APP_NAME`).
- **Branding**: Do not use YouTube's name, logo, red play-button mark, or trade dress for the app's own branding. The layout can feel familiar, but the brand must be original.
- **Primary Deployment Target**: **Synology DS425+ NAS** (Intel Celeron J4125, x86_64, 2 GB RAM, DSM 7.x Container Manager), exposed to the internet only through a **Cloudflare Tunnel** at `utube.vajapravin.me`. Must also run unchanged on any Linux or macOS laptop for development.
- **Port Constraints**: Strictly avoid forbidden host ports (`70`, `71`, `8088`, `5173`, `8086`, `6389`, `6379`, `8082`, `8000`, `8084`, `8085`, `80`, `443`, `5000`, `32768`, `9000`, `5433`, `6543`, `8004`, `8083`, `3002`, `8002`, `8081`, `8080`, `3000`, `5432`) and existing `chatapp` ports (`3001`, `8001`, `1883`, `9001`, `4223`, `5435`, `6380`).

---

## 1. Product Scope

### 1.1 In Scope (v1)
1. **Google OIDC Authentication**: Sign-in with Google (OIDC, PKCE, BFF pattern). No local passwords.
2. **Onboarding**: Category picker requiring 3–10 interest selections.
3. **Dashboard (Home)**: Horizontal shelf per selected interest category plus a deduplicated "For you" grid.
4. **AI-Curated Channels**: Natural language prompt-driven channels filled with videos and shorts via LLM pipeline.
5. **Channel Page**: Header with banner/avatar, prompt info (owner only), and three tabs: **Videos**, **Shorts**, and **Liked**.
6. **Watch Page**: Embedded player (`youtube-nocookie.com`), metadata, and **Like**, **Share**, and **Save** actions.
7. **Playlists**: Create, rename, delete, add/remove, and keyboard/drag-and-drop reordering with Lexorank. Built-in "Watch later" and "Liked videos".
8. **Thumbnails**: Responsive, lazy-loaded thumbnails across all cards.
9. **Local Search**: Fast search over cached catalog (videos, channels) via PostgreSQL `tsvector` and `pg_trgm`.

### 1.2 Out of Scope (v1)
Uploading/hosting video files, user comments, social subscriptions between users, monetization, live streams, notifications, native mobile apps, and downloading or re-hosting YouTube media.

### 1.3 Personas
- **Owner (Primary)**: Pravin. Self-hosts on home NAS to curate technical, learning, and leisure channels.
- **Invited User (Secondary)**: Family and friends permitted via Google email allow-list (`ALLOWED_EMAILS`).

### 1.4 Key Assumptions
- **A1. Video Source**: Metadata from YouTube Data API v3 (free tier default, 10,000 units/day). Playback via YouTube IFrame Player (`youtube-nocookie.com`). LLM never invents video IDs.
- **A2. Shorts Definition**: Video duration ≤ 180s (post-Oct 2024 YouTube limit) OR title/description contains `#shorts`. Optional strict probe via HTTP HEAD to `youtube.com/shorts/{id}`.
- **A3. Liked Tab**: Displays videos in that channel liked by the current user. Global liked view available under `/me/likes`.
- **A4. Access Model**: Registration restricted to `ALLOWED_EMAILS` and `ALLOWED_DOMAINS` unless `OPEN_REGISTRATION=true`.
- **A5. Channel Visibility**: `private` by default (returns 404 to non-owners). `unlisted` viewable by link. `public` listed on `/explore`.

---

## 2. Hard Constraints

1. **No Paid Services Default**: All external APIs use free tiers or local mocks by default.
2. **Tech Stack**:
   - Backend: Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, managed by `uv`.
   - Frontend: React 18, TypeScript (strict), Vite, Tailwind CSS, Radix UI, TanStack Query v5, managed by `pnpm`.
   - Reverse Proxy: Caddy 2 for static SPA delivery, API reverse-proxying, and security headers.
   - Database: PostgreSQL 16 (Alpine) with `uuid-ossp` and `pg_trgm`.
   - Cache / Queue: Redis 7 (Alpine), maxmemory 64mb, LRU eviction.
   - Job Runner: `arq` (asyncio Redis queue).
3. **Memory Budget**: `core` compose profile total active RAM **≤ 1.0 GB**. Per-container memory caps (`mem_limit`).
4. **Networking & Ingress**: Ingress via Cloudflare Tunnel (`utube.vajapravin.me`). Single-origin routing through Caddy (`/` -> React SPA, `/api/*` -> FastAPI).
5. **YouTube API Terms of Service Compliance**:
   - Official embedded player only.
   - No stream downloading or offline saving.
   - Display "Content from YouTube" attribution and original link.
   - 30-day automatic metadata TTL purge.
   - Zero YouTube account OAuth scopes requested.

---

## 3. Architecture & Container Allocation

| Container | Image / Base | Responsibility | Profile | mem_limit | Host Port |
|---|---|---|---|---|---|
| `web` | Caddy 2 Alpine | Serves React SPA, reverse-proxies `/api`, sets CSP | core | 64 MB | `3005:80` |
| `api` | Python 3.12 Slim | FastAPI REST, OIDC BFF, sessions, business logic | core | 256 MB | `8005:8000` (dev) |
| `worker` | Python 3.12 Slim | arq worker: curation, category refresh, 30-day purge | core | 256 MB | — |
| `postgres` | Postgres 16 Alpine | Relational system of record, GIN search | core | 256 MB | `5436:5432` |
| `redis` | Redis 7 Alpine | Sessions, rate limits, quota counter, job queue | core | 96 MB | `6381:6379` |
| `migrate` | Python 3.12 Slim | One-shot DB migration & category seed runner | core | 128 MB | — (exits 0) |
| `mock-oidc`| Navikt Mock OAuth2 | Simulated Google OIDC provider for tests | test | 128 MB | `8087:8080` |
| `cloudflared`| Cloudflare Alpine | Standalone tunnel (optional dev profile) | cloudflare | 48 MB | — |
| `ollama` | Ollama | Local offline LLM runner | llm-local | 3 GB | — |
