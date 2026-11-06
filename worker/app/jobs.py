"""arq background job handlers and cron triggers."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from arq.connections import RedisSettings
from arq.cron import cron
from redis import asyncio as aioredis
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_worker_settings
from app.curation.pipeline import execute_curation_pipeline
from app.models.category import CategoryVideo
from app.providers.llm import FakeLLMProvider, GeminiProvider
from app.providers.video_source import FakeVideoSource, YouTubeDataAPISource

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

    # Auto-seed category videos on cold-start if cache is empty
    try:
        async with ctx["session_factory"]() as session:
            res = await session.execute(select(CategoryVideo).limit(1))
            if res.scalar_one_or_none() is None:
                logger.info("cold_start_refresh_categories_triggering")
                asyncio.create_task(refresh_categories_job(ctx))
    except Exception as exc:
        logger.warning("cold_start_category_refresh_failed", error=str(exc))


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


async def refresh_categories_job(ctx: Dict[Any, Any]) -> int:
    """Fetch and refresh popular videos for all active categories."""
    import re

    from app.models.category import Category, CategoryVideo
    from app.models.video import Video

    session_factory = ctx["session_factory"]
    video_source = ctx["video_source"]
    total_refreshed = 0

    async with session_factory() as session:
        stmt = select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order)
        res = await session.execute(stmt)
        categories = res.scalars().all()

        for category in categories:
            query = category.seed_queries[0] if category.seed_queries else category.name
            raw_candidates = await video_source.search(query=query, max_results=15)
            video_ids = [
                item["id"]["videoId"]
                for item in raw_candidates
                if isinstance(item.get("id"), dict) and "videoId" in item["id"]
            ]
            if not video_ids:
                continue

            details = await video_source.get_video_details(video_ids)
            for rank, item in enumerate(details):
                snippet = item.get("snippet", {})
                content_details = item.get("contentDetails", {})
                statistics = item.get("statistics", {})

                # duration
                dur_str = content_details.get("duration", "PT0S")
                m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", dur_str)
                h = int(m.group(1) or 0) if m else 0
                mins = int(m.group(2) or 0) if m else 0
                s = int(m.group(3) or 0) if m else 0
                duration_s = h * 3600 + mins * 60 + s

                yt_id = item["id"]
                pub_raw = snippet.get("publishedAt", "2024-01-01T00:00:00Z").replace("Z", "+00:00")
                try:
                    pub_dt = datetime.fromisoformat(pub_raw)
                except Exception:
                    pub_dt = datetime.now(timezone.utc)

                vid_insert = (
                    insert(Video)
                    .values(
                        id=uuid.uuid4(),
                        youtube_id=yt_id,
                        title=snippet.get("title", ""),
                        description=snippet.get("description", ""),
                        source_channel_id=snippet.get("channelId"),
                        source_channel_title=snippet.get("channelTitle"),
                        duration_s=duration_s,
                        is_short=(duration_s <= 180),
                        aspect="portrait" if duration_s <= 180 else "landscape",
                        thumbnails=snippet.get("thumbnails", {}),
                        published_at=pub_dt,
                        view_count=int(statistics.get("viewCount", 0))
                        if statistics.get("viewCount")
                        else None,
                        like_count=int(statistics.get("likeCount", 0))
                        if statistics.get("likeCount")
                        else None,
                        fetched_at=datetime.now(timezone.utc),
                    )
                    .on_conflict_do_update(
                        index_elements=["youtube_id"],
                        set_={
                            "title": snippet.get("title", ""),
                            "description": snippet.get("description", ""),
                            "duration_s": duration_s,
                            "thumbnails": snippet.get("thumbnails", {}),
                            "view_count": int(statistics.get("viewCount", 0))
                            if statistics.get("viewCount")
                            else None,
                            "like_count": int(statistics.get("likeCount", 0))
                            if statistics.get("likeCount")
                            else None,
                            "fetched_at": datetime.now(timezone.utc),
                        },
                    )
                    .returning(Video.id)
                )
                vid_res = await session.execute(vid_insert)
                vid_id = vid_res.scalar_one()

                cat_vid_insert = (
                    insert(CategoryVideo)
                    .values(
                        category_id=category.id,
                        video_id=vid_id,
                        rank=rank,
                        refreshed_at=datetime.now(timezone.utc),
                    )
                    .on_conflict_do_update(
                        index_elements=["category_id", "video_id"],
                        set_={
                            "rank": rank,
                            "refreshed_at": datetime.now(timezone.utc),
                        },
                    )
                )
                await session.execute(cat_vid_insert)
                total_refreshed += 1

        await session.commit()
    logger.info("refreshed_categories_job_complete", total_refreshed=total_refreshed)
    return total_refreshed


class ArqWorkerSettings:
    settings = get_worker_settings()
    # Connect to redis queue
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    functions = [curate_channel_job, purge_stale_metadata_job, refresh_categories_job]
    cron_jobs = [
        cron(refresh_categories_job, hour={0, 12}, minute=0),
        cron(purge_stale_metadata_job, hour=3, minute=0),
    ]
    max_jobs = 5
    job_timeout = 600
