# ADR 0007: Non-Conflicting Port Allocation Strategy

- **Status**: Accepted
- **Date**: 2026-11-03
- **Deciders**: Full-Stack Architecture Team

---

## Context and Problem Statement
The developer workstation and Synology NAS run multiple concurrent applications (`chatapp`, `file2md`, `vocab-learner`, `trove`, `portfolio`, `google-tasks-rest-api`). The user explicitly mandated avoiding 26 forbidden ports plus all active ports used by other local services.

## Forbidden Ports Checklist
`70`, `71`, `80`, `443`, `3000`, `3002`, `5000`, `5173`, `5432`, `5433`, `6379`, `6380`, `6389`, `6543`, `8000`, `8002`, `8004`, `8080`, `8081`, `8082`, `8083`, `8084`, `8085`, `8086`, `8088`, `9000`, `32768`.
Additionally, `chatapp` uses: `3001` (web), `8001` (api), `1883`/`9001` (mosquitto), `4223` (nats), `5435` (postgres), `6380` (redis).

## Decision Drivers
- Zero port collisions when running all services concurrently.
- Clear, memorable port scheme parameterized via `.env`.
- Easy binding in container manifests.

## Considered Options
- **Option 1**: Dynamic random high-port assignment (`0:8000`).
- **Option 2**: Systematic static assignment of completely unused ports.

## Decision Outcome
Chosen option: **Option 2: Systematic static assignment of completely unused ports**.

### Port Allocation:
1. **`WEB_PORT = 3005`**: Caddy HTTP ingress proxy (maps to container port 80).
2. **`API_PORT = 8005`**: FastAPI direct backend access (maps to container port 8000).
3. **`POSTGRES_PORT = 5436`**: PostgreSQL 16 database (maps to container port 5432).
4. **`REDIS_PORT = 6381`**: Redis 7 cache & queue (maps to container port 6379).
5. **`MOCK_OIDC_PORT = 8087`**: Navikt Mock OAuth2 server for test profile (maps to container port 8080).

## Consequences
- **Positive**: 100% collision-free; fully parameterized via `.env`; predictable for local development and test automation.
- **Negative**: None.
