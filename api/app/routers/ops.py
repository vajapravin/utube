"""Operations, healthchecks, and Prometheus metrics."""

from fastapi import APIRouter, Depends, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis import asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_redis

router = APIRouter(tags=["Operations"])


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict[str, str]:
    """Process liveness probe."""
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness probe")
async def readyz(
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> dict[str, str]:
    """Readiness probe checking Postgres and Redis connectivity."""
    # Check DB
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        return Response(
            content=f"Database not ready: {exc}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Check Redis
    try:
        await redis_client.ping()
    except Exception as exc:
        return Response(
            content=f"Redis not ready: {exc}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return {"status": "ready"}


@router.get("/metrics", summary="Prometheus metrics")
async def metrics() -> Response:
    """Internal Prometheus metrics endpoint (blocked from external ingress)."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
