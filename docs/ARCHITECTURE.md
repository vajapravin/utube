# System Architecture: `mytube`

This document details the software and systems architecture for **`mytube`**, a self-hosted personal AI-curated video platform.

---

## 1. High-Level Architecture

The platform follows a **Single-Origin Backend-for-Frontend (BFF)** topology, running entirely inside Docker Compose on a single node (Synology DS425+ NAS or local developer machine).

```
                      Internet
                         │
                         ▼
             Cloudflare Edge Network
             (https://utube.vajapravin.me)
                         │
                         │ Cloudflare Tunnel (QUIC / TLS)
                         ▼
        ┌──────────────────────────────────────────────┐
        │ Existing cloudflared Daemon (NAS Host)       │
        └──────────────────────┬───────────────────────┘
                               │ Host Port 3005
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Docker Network: "mytube_net"                                           │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ web (Caddy 2, mem: 64MB)                                         │  │
│  │   ├── /           ──► Compiled React 18 SPA (static assets)      │  │
│  │   └── /api/*      ──► Reverse-proxy to api:8000                  │  │
│  └───────────────────┬──────────────────────────────────────────────┘  │
│                      │                                                 │
│                      ▼                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ api (FastAPI / Uvicorn, mem: 256MB)                              │  │
│  │   ├── Google OIDC PKCE Auth (BFF Pattern)                        │  │
│  │   ├── REST Endpoints (/api/v1/*)                                 │  │
│  │   ├── Scoped Repositories (owner_id enforcement)                 │  │
│  │   └── Redis Session & Quota Checking                             │  │
│  └────────┬──────────────────────────┬──────────────────────────────┘  │
│           │                          │                                 │
│           ▼                          ▼                                 │
│  ┌──────────────────┐       ┌───────────────────────────────────────┐  │
│  │ postgres:16      │       │ redis:7                               │  │
│  │ (mem: 256MB)     │       │ (mem: 96MB)                           │  │
│  │ Port 5436        │       │ Port 6381                             │  │
│  │ System of Record │       │ Sessions, Quota, Cache, arq queue     │  │
│  └──────────────────┘       └──────────────────┬────────────────────┘  │
│                                                │                       │
│                                                ▼                       │
│                             ┌───────────────────────────────────────┐  │
│                             │ worker (arq, mem: 256MB)              │  │
│                             │   ├── Channel Curation Pipeline       │  │
│                             │   ├── Category Refresh Cron           │  │
│                             │   └── 30-Day YouTube Metadata Purge   │  │
│                             └──────┬───────────────────────┬────────┘  │
└────────────────────────────────────┼───────────────────────┼───────────┘
                                     │                       │
                                     ▼                       ▼
                        YouTube Data API v3         LLM Provider
                        (HTTPS Outbound)            (Gemini 2.5 Flash / Ollama)
```

---

## 2. Infrastructure Patterns & Alignment with `chatapp`

Following [`~/Documents/aml/chatapp/docker-compose.yml`](file:///Users/pravinmacm4/Documents/aml/chatapp/docker-compose.yml), `mytube` mirrors its resource management and service patterns:

### 2.1 Cloudflare Ingress Strategy
- In `chatapp`, the embedded `cloudflared` container was removed from `core` docker-compose to leverage the existing host-level Cloudflare Tunnel daemon on the Synology NAS.
- `mytube` implements the identical approach:
  - Caddy binds to **`WEB_PORT=3005`** on the host.
  - The NAS host's Cloudflare Zero Trust tunnel routes `utube.vajapravin.me` -> `http://localhost:3005`.
  - For standalone dev testing, an optional `cloudflare` compose profile provides an isolated containerized tunnel without polluting the host.

### 2.2 PostgreSQL Database
- **Image**: `postgres:16-alpine`
- **Memory Ceiling**: `256m`
- **Host Port**: `5436:5432` (eliminates collisions with 5432, 5433, 5435, 6543)
- **Init Script**: `./deploy/postgres/init.sql` loads `uuid-ossp` and `pg_trgm` extensions.
- **Connection**: Managed with SQLAlchemy 2.0 (asyncio) via `asyncpg`.

### 2.3 Redis Cache & Job Broker
- **Image**: `redis:7-alpine`
- **Memory Ceiling**: `96m`
- **Host Port**: `6381:6379` (eliminates collisions with 6379, 6380, 6389)
- **Eviction & Persistence**: `redis-server --port 6381 --maxmemory 64mb --maxmemory-policy allkeys-lru --save 60 1`.
- **Usage**:
  - DB 0: Active user sessions, sliding-window rate limit counters, Pacific-Time daily quota tracker.
  - DB 1: Shared category feed and search result cache.
  - DB 2: `arq` task queues.

---

## 3. Strict Port Allocation Matrix

To prevent port conflicts across the user's host machine (which already runs `chatapp`, `file2md`, `vocab-learner`, `trove`, `portfolio`, and macOS system services):

| Service | Environment Variable | Port | Collision Verification |
|---|---|---|---|
| **Caddy Ingress** | `WEB_PORT` | **`3005`** | ✅ Not in forbidden list (3000, 3001, 3002). Available on host. |
| **FastAPI Dev** | `API_PORT` | **`8005`** | ✅ Not in forbidden list (8000, 8001, 8002, 8004, 8080-8088). |
| **PostgreSQL 16** | `POSTGRES_PORT` | **`5436`** | ✅ Not in forbidden list (5432, 5433, 5435, 6543). |
| **Redis 7** | `REDIS_PORT` | **`6381`** | ✅ Not in forbidden list (6379, 6380, 6389). |
| **Mock-OIDC** | `MOCK_OIDC_PORT` | **`8087`** | ✅ Not in forbidden list (8080-8086, 8088). Available for test profile. |

---

## 4. Hardware Constraints & Memory Ceiling (Synology DS425+)

The Synology DS425+ NAS features an Intel Celeron J4125 quad-core CPU and **2 GB RAM**.
- DSM 7.x OS consumes ~500 MB.
- Existing containers (`chatapp`, etc.) consume ~300 MB.
- **`mytube` Core Profile Budget**: Strict ceiling of **≤ 1.0 GB RAM**.

| Service | Container Memory Limit | Typical Measured Active RAM |
|---|---|---|
| `web` (Caddy 2) | 64 MB | ~15 MB |
| `api` (FastAPI / asyncpg) | 256 MB | ~65 MB |
| `worker` (arq / httpx) | 256 MB | ~70 MB |
| `postgres` (PostgreSQL 16) | 256 MB | ~35 MB |
| `redis` (Redis 7) | 96 MB | ~12 MB |
| **Combined Core Stack** | **928 MB Ceiling** | **~197 MB Active** |

---

## 5. AI Curation Pipeline Architecture

```
User Prompt (e.g., "Beginner ESP32 IoT projects under 20 minutes")
   │
   ▼
1. Plan (LLM structured prompt -> Pydantic ChannelPlan)
   Queries [3..8], must_include, exclude_terms, duration bounds
   │
   ▼
2. Retrieve (YouTube Data API v3)
   search.list (100 units/query) + videos.list (1 unit/50 videos)
   │
   ▼
3. Pre-Filter (Deterministic logic in Python - zero LLM tokens)
   Drop excluded keywords, enforce duration bounds, drop made-for-kids
   Caps candidate list at max 150 videos
   │
   ▼
4. Rank (LLM batch evaluation in chunks of 30 candidates)
   Returns {id, relevance_score 0-100, kind, reason}
   Drops any hallucinated IDs not present in candidate batch
   │
   ▼
5. Select (Deterministic categorization)
   Keep scores >= CURATION_MIN_SCORE (60)
   Partition into Videos and Shorts (using 180s heuristic + aspect check)
   │
   ▼
6. Persist (PostgreSQL upsert)
   Insert into videos, channel_videos, and log channel_curation_runs
```

---

## 6. Data Model Overview

All primary keys use **UUIDv7** (time-ordered, highly indexable, guess-resistant). All timestamps are UTC `timestamptz`.

- **`users`**: User identity linked to Google `sub`. Stores settings (theme, autoplay, history pause).
- **`categories`**: Catalog seeded from `seed/categories.yaml`.
- **`user_interests`**: Many-to-many relationship tracking user category choices (3–10 items).
- **`videos`**: Central cached repository of YouTube video metadata with GIN full-text search vector.
- **`category_videos`**: Mapped videos displayed on Home category shelves.
- **`channels`**: User-created AI channels defined by prompts, latest plan, and visibility.
- **`channel_videos`**: Curated videos mapped to channels with curation scores and pinned flags.
- **`channel_exclusions`**: Videos manually removed by the channel owner (never reintroduced on refresh).
- **`channel_curation_runs`**: Historical telemetry of curation executions (tokens, units, duration, errors).
- **`likes`**: User likes mapped to videos.
- **`hidden_videos`**: "Not interested" exclusions per user.
- **`playlists`**: User playlists including built-in "Watch later".
- **`playlist_items`**: Ordered items using Lexorank strings for O(1) single-row repositioning.
- **`watch_history`**: User playback progress sampled every 15 seconds.
- **`audit_logs`**: Security events (logins, access denials, account deletion).
