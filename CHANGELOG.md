# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

## [0.0.1] - 2026-11-03
### Added
- Phase 0: Project bootstrap, repository layout, tooling configurations, Makefile, and ADRs.
