# mytube — Personal AI-Curated Video Web App

A production-grade, self-hosted personal video web application that functions like a minimal YouTube with AI-driven curation channels. Built to run with Docker Compose on a **Synology DS425+ NAS** (2 GB RAM) behind a **Cloudflare Tunnel** at `utube.vajapravin.me`, and locally on macOS/Linux.

---

## Architecture Overview

```
Browser (SPA)
  └─ HTTPS ─► Cloudflare ─► cloudflared ─► caddy:3005 (web)
                                              ├─ /           → React SPA (immutable static assets)
                                              └─ /api/*      → api:8000 (FastAPI)

Docker Network ("mytube_net"):
  web (Caddy 2, mem: 64MB)
  api (FastAPI, mem: 256MB)        ◄─► postgres:16 (5436) (system of record)
  worker (arq, mem: 256MB)         ◄─► redis:7 (6381)     (sessions, rate limits, quota)
  migrate (Alembic one-shot)
```

- **Strict Resource Budget**: Entire `core` compose profile consumes **≤ 1.0 GB active RAM**.
- **No Conflict Ports**: Configured to avoid all forbidden ports:
  - `WEB_PORT`: **`3005`**
  - `API_PORT`: **`8005`**
  - `POSTGRES_PORT`: **`5436`**
  - `REDIS_PORT`: **`6381`**
  - `MOCK_OIDC_PORT`: **`8087`**

---

## Features

- **Google Sign-In (OIDC BFF)**: OAuth 2.0 PKCE, server-side Redis sessions (`__Host-` cookies), double-submit CSRF, and strict email allow-list.
- **Interest Onboarding**: Mandatory selection of 3–10 topic categories to personalize the dashboard.
- **Dashboard & Category Shelves**: Horizontal shelves, "For you" deduplicated grid, and vertical Shorts shelf.
- **AI-Curated Channels**: Prompt-driven channels populated through an LLM pipeline (Gemini 2.5 Flash free tier default / Ollama).
- **Embedded Player**: YouTube IFrame Player (`youtube-nocookie.com`), with local like/save/share actions.
- **Playlists & Watch Later**: Lexorank-ordered drag-and-drop playlists with keyboard navigation.
- **Legal & ToS Compliant**: No video downloads, 30-day automatic metadata TTL purge, required attribution.

---

## Quickstart

### Prerequisites
- Python 3.12+ with `uv`
- Node.js 20+ with `pnpm`
- Docker & Docker Compose v2.20+

### Start Stack
```bash
cp .env.example .env
make up
make logs
```

### Run Tests & Verification
```bash
make test
make lint
```

For detailed documentation, refer to:
- [`docs/BRIEF.md`](./docs/BRIEF.md): Canonical project requirements.
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md): System design & data models.
- [`docs/SECURITY.md`](./docs/SECURITY.md): ASVS Level 2 security standards.
- [`docs/RUNBOOK.md`](./docs/RUNBOOK.md): Operations, credentials, and Synology deployment guide.
