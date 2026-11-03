"""arq background job handlers and cron triggers."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from app.providers.llm import FakeLLMProvider, GeminiProvider
from app.providers.video_source import FakeVideoSource, YouTubeDataAPISource
from arq.connections import RedisSettings
from redis import asyncio as aioredis
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_worker_settings
from app.curation.pipeline import execute_curation_pipeline

logger = logging.getLogger("mytube.worker")


async def startup(ctx: Dict[Any, Any]) -> None:
    settings = get_worker_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    ctx["engine"] = engine
    ctx["session_factory"] = async_sessionmaker(engine, expire_on_commit=False)
    ctx["redis"] = aioredis.from_url(settings.REDIS_URL)

    # Initialize video source & LLM provider
    if settings.VIDEO_SOURCE == "fake":
        ctx["video_source"] = FakeVideoSource()
    else:
        ctx["video_source"] = YouTubeDataAPISource(api_key=settings.YT_API_KEY)

    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        ctx["llm_provider"] = GeminiProvider(
            api_key=settings.GEMINI_API_KEY, model=settings.LLM_MODEL
        )
    else:
        ctx["llm_provider"] = FakeLLMProvider()

    logger.info("worker_started")


async def shutdown(ctx: Dict[Any, Any]) -> None:
    if "engine" in ctx:
        await ctx["engine"].dispose()
    if "redis" in ctx:
        await ctx["redis"].close()
    logger.info("worker_shutdown")


async def curate_channel_job(ctx: Dict[Any, Any], channel_id_str: str) -> Dict[str, Any]:
    """Execute curation pipeline for a single channel."""
    channel_id = uuid.UUID(channel_id_str)
    settings = get_worker_settings()
    session_factory = ctx["session_factory"]

    async with session_factory() as session:
        result = await execute_curation_pipeline(
            channel_id=channel_id,
            session=session,
            settings=settings,
            video_source=ctx["video_source"],
            llm_provider=ctx["llm_provider"],
            trigger="manual",
        )
    return result


async def purge_stale_metadata_job(ctx: Dict[Any, Any]) -> int:
    """Purge YouTube metadata older than 30 days to strictly adhere to YouTube API ToS."""
    from app.models.video import Video

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    session_factory = ctx["session_factory"]

    async with session_factory() as session:
        # Note: Videos that are liked, pinned, or in playlists can be retained or re-fetched;
        # stale unreferenced category/search videos are purged.
        stmt = delete(Video).where(Video.fetched_at < cutoff)
        res = await session.execute(stmt)
        await session.commit()
        purged_count = res.rowcount
    logger.info("purged_stale_youtube_metadata", count=purged_count)
    return purged_count


class ArqWorkerSettings:
    settings = get_worker_settings()
    # Connect to redis queue
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    functions = [curate_channel_job, purge_stale_metadata_job]
    max_jobs = 5
    job_timeout = 600
