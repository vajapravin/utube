# ADR 0003: Redis-Backed `arq` vs. Celery / RQ for Asynchronous Task Processing

- **Status**: Accepted
- **Date**: 2026-11-03
- **Deciders**: Full-Stack Architecture Team

---

## Context and Problem Statement
Background tasks (channel curation pipelines, category refreshes, metadata purges) must be executed asynchronously without blocking FastAPI HTTP requests. We need a lightweight Python task queue.

## Decision Drivers
- Memory footprint on the 2 GB Synology NAS (target < 75 MB active RAM for worker).
- Native integration with Python 3.12 `asyncio`.
- Operational simplicity: no additional broker daemon (e.g. RabbitMQ).
- Shared use of the existing Redis 7 instance.

## Considered Options
- **Option 1**: Celery + RabbitMQ or Redis.
- **Option 2**: RQ (Redis Queue - synchronous / multiprocessing).
- **Option 3**: `arq` (asyncio job queue based on Redis).

## Decision Outcome
Chosen option: **Option 3: `arq` (asyncio job queue based on Redis)**.

### Rationale:
- Celery has significant dependency weight and higher idle memory footprint (~80–120 MB RAM per worker process) and complex configuration.
- RQ relies on `fork()` and process pools, which do not integrate cleanly with modern `asyncio` networking libraries (`httpx`, `asyncpg`).
- `arq` runs entirely inside a single Python `asyncio` event loop. It consumes under 60 MB RAM, supports scheduled cron triggers, automatic retries with backoff, job health checks, and connects directly to the existing Redis container.

## Consequences
- **Positive**: Extremely low memory usage (~40–60 MB RAM); native `async/await` execution with HTTPX and SQLAlchemy; zero extra brokers.
- **Negative**: Single-process event loop (sufficient for I/O-bound API and LLM calls; worker container can be scaled horizontally if necessary).
