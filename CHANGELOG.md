# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-11-04

### Added
- **Category Ingestion Engine**: Background arq worker job (`refresh_categories_job`) populating 20 default system interest categories with active videos.
- **AI Channel Curation Pipeline**: 6-stage autonomous curation engine (`execute_curation_pipeline`) combining prompt plan generation, search candidate querying, deterministic pre-filtering (0 LLM tokens), LLM scoring and rationale generation, LexoRank ordering, and audit runs tracking.
- **Personalized Feeds**: Home shelves (`/api/v1/feed/home`), category grids (`/api/v1/feed/categories/{slug}`), continue watching history shelf, and shorts shelf.
- **Engagement & Interactions**: Video liking/unliking (`PUT/DELETE /api/v1/videos/{youtube_id}/like`), hiding (`PUT /api/v1/videos/{youtube_id}/hide`), and watch progress tracking (`PUT /api/v1/videos/{youtube_id}/progress`).
- **User Playlists**: Full CRUD (`/api/v1/playlists`), item insertion, LexoRank midpoint reordering, and video membership lookup (`/api/v1/videos/{youtube_id}/saved-in`).
- **Local Catalogue Search**: Fast hybrid search via PostgreSQL `search_tsv` full-text index with `pg_trgm` fuzzy similarity fallback (`/api/v1/search`).
- **Docker Compose Core Stack**: End-to-end multi-container stack deployment verified live on ports `3005`, `8005`, `5436`, `6381`, operating under ~360 MiB total RAM (budget ≤ 1.0 GB for Synology DS425+ NAS).
- **Caddy Ingress & Metrics**: Caddy reverse proxy routing `/api/*`, `/healthz`, `/readyz`, and `/metrics` directly to FastAPI with CSP, HSTS, and frame protection.

## [0.1.0] - 2026-11-03

### Added
- Core compose stack with Caddy single-origin reverse proxy (`WEB_PORT=3005`).
- FastAPI backend (`API_PORT=8005`) with async SQLAlchemy, Alembic, structured logging, healthchecks, and metrics.
- Google OIDC authentication via PKCE (BFF architecture) with Redis session storage and CSRF protection.
- Allow-list access control via `ALLOWED_EMAILS` and `ALLOWED_DOMAINS`.
- PostgreSQL 16 Alpine configuration with `uuid-ossp` and `pg_trgm` extensions (`POSTGRES_PORT=5436`).
- Redis 7 Alpine configuration with LRU memory eviction (`REDIS_PORT=6381`).
- React 18 TypeScript frontend shell with Tailwind CSS, Lucide icons, and theme provider.
- Complete documentation suite (`BRIEF.md`, `ARCHITECTURE.md`, `SECURITY.md`, `THREAT_MODEL.md`, `API.md`, `RUNBOOK.md`, and ADRs 0001–0007).
- CI workflow with linting, typing, unit tests, and Trivy security scanning.
