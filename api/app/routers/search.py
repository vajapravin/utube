"""Local catalogue & YouTube career search router with anti-entertainment guardrails."""

import re
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.deps import get_current_user, get_db
from app.models.user import User
from app.providers.video_source import FakeVideoSource, YouTubeDataAPISource
from app.repositories.video_repo import VideoRepository
from app.schemas.video import VideoResponse
from mytube_shared.guardrails import (
    build_career_focused_queries,
    evaluate_career_relevance,
    is_entertainment_or_clickbait,
)

router = APIRouter(prefix="/search", tags=["Search"])


def _parse_duration(duration_str: str) -> int:
    if not duration_str:
        return 0
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


async def _get_video_source(settings: Settings) -> YouTubeDataAPISource | FakeVideoSource:
    if settings.VIDEO_SOURCE == "fake":
        return FakeVideoSource()
    return YouTubeDataAPISource(api_key=settings.YT_API_KEY)


@router.get("", response_model=List[VideoResponse], summary="Search career learning videos")
async def search(
    q: str = Query(..., min_length=1, max_length=100),
    filter_type: Optional[str] = Query(None, description="all | tutorials | talks | courses"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Sequence[VideoResponse]:
    video_repo = VideoRepository(db)

    # 1. Reject search queries that are explicitly asking for entertainment or memes
    if is_entertainment_or_clickbait(q, ""):
        return []

    # 2. Local database search
    videos = list(await video_repo.search_local(query=q, limit=30))

    # 3. If local results are low (< 8) and YouTube API is available, fetch live career videos
    if len(videos) < 8:
        source = await _get_video_source(settings)
        # Augment query for career/educational focus if it's broad
        career_queries = build_career_focused_queries(q)
        search_query = career_queries[0] if career_queries else f"{q} tutorial engineering"

        raw_items = await source.search(
            query=search_query,
            max_results=15,
            videoDuration="medium",
        )

        yt_ids = []
        for item in raw_items:
            vid_id = item.get("id")
            if isinstance(vid_id, dict):
                vid_id = vid_id.get("videoId")
            if vid_id and len(vid_id) == 11:
                snippet = item.get("snippet", {})
                title = snippet.get("title", "")
                desc = snippet.get("description", "")
                # Apply anti-entertainment guardrail
                if not is_entertainment_or_clickbait(title, desc):
                    yt_ids.append(vid_id)

        if yt_ids:
            details = await source.get_video_details(yt_ids)
            for d in details:
                snippet = d.get("snippet", {})
                content_details = d.get("contentDetails", {})
                stats = d.get("statistics", {})

                title = snippet.get("title", "Untitled")
                desc = snippet.get("description", "")
                if is_entertainment_or_clickbait(title, desc):
                    continue

                duration_s = _parse_duration(content_details.get("duration", "PT10M")) or 600
                is_short = duration_s <= settings.SHORTS_MAX_SECONDS

                v = await video_repo.upsert_video({
                    "youtube_id": d.get("id"),
                    "title": title,
                    "description": desc,
                    "source_channel_id": snippet.get("channelId"),
                    "source_channel_title": snippet.get("channelTitle"),
                    "duration_s": duration_s,
                    "is_short": is_short,
                    "aspect": "vertical" if is_short else "landscape",
                    "thumbnails": snippet.get("thumbnails", {}),
                    "published_at": snippet.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                })
                # Avoid duplicates
                if not any(existing.youtube_id == v.youtube_id for existing in videos):
                    videos.append(v)

    # 4. Filter by requested filter_type if specified
    if filter_type == "courses":
        videos = [v for v in videos if "course" in v.title.lower() or v.duration_s >= 1800]
    elif filter_type == "tutorials":
        videos = [v for v in videos if "tutorial" in v.title.lower() or "how to" in v.title.lower()]
    elif filter_type == "talks":
        videos = [v for v in videos if "talk" in v.title.lower() or "conference" in v.title.lower()]

    items = []
    for v in videos:
        # Final pass: never return entertainment / clickbait
        if is_entertainment_or_clickbait(v.title, v.description or ""):
            continue
        is_liked = await video_repo.is_liked_by_user(current_user.id, v.id)
        items.append(
            VideoResponse.model_validate({**v.__dict__, "is_liked": is_liked, "is_saved": False})
        )
    return items
