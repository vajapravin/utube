"""Channels router: CRUD, plan preview, curation triggering, tabs, and manual curation."""

import re
import uuid
from typing import List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.deps import (
    check_csrf,
    get_current_user,
    get_current_user_optional,
    get_db,
    get_rate_limiter,
)
from app.models.channel import Channel
from app.models.user import User
from app.providers.llm import FakeLLMProvider, GeminiProvider, LLMProvider
from app.providers.video_source import FakeVideoSource, YouTubeDataAPISource
from app.repositories.channel_repo import ChannelRepository
from app.repositories.video_repo import VideoRepository
from app.schemas.channel import (
    ChannelCreate,
    ChannelPlan,
    ChannelResponse,
    ChannelUpdate,
    PreviewPlanRequest,
)
from app.schemas.common import CursorPage
from app.schemas.video import VideoResponse
from app.security.rate_limit import RateLimiter

router = APIRouter(prefix="/channels", tags=["Channels"])


def _slugify(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", name).strip().lower()
    return re.sub(r"[-\s]+", "-", s)


async def _get_llm_provider(settings: Settings) -> LLMProvider:
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.LLM_MODEL)
    return FakeLLMProvider()


@router.post(
    "",
    response_model=ChannelResponse,
    summary="Create a new AI channel",
    dependencies=[Depends(check_csrf)],
)
async def create_channel(
    payload: ChannelCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings),
) -> ChannelResponse:
    # Rate limit: 20 channel creations per day per user (SEC-06)
    await rate_limiter.check_rate_limit(
        f"create_channel:{current_user.id}", max_requests=20, window_seconds=86400
    )

    channel_repo = ChannelRepository(db)

    # Generate or validate handle
    raw_handle = payload.handle or f"@{_slugify(payload.name)}"
    if not raw_handle.startswith("@"):
        raw_handle = f"@{raw_handle}"

    try:
        channel = await channel_repo.create_channel(
            owner_id=current_user.id,
            name=payload.name,
            handle=raw_handle,
            description=payload.description,
            prompt=payload.prompt,
            visibility=payload.visibility,
            banner_style=payload.banner_style,
            category_ids=payload.category_ids,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create channel: {exc}",
        )

    # In production, enqueue job via arq; for synchronous fallback update status to ready
    channel.status = "ready"
    await db.commit()

    return ChannelResponse.model_validate(
        {**channel.__dict__, "is_owner": True, "video_count": 0, "short_count": 0}
    )


@router.get("", response_model=List[ChannelResponse], summary="List user's channels")
async def list_my_channels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Sequence[ChannelResponse]:
    channel_repo = ChannelRepository(db)
    channels = await channel_repo.list_by_owner(current_user.id)
    return [
        ChannelResponse.model_validate(
            {**ch.__dict__, "is_owner": True, "video_count": 0, "short_count": 0}
        )
        for ch in channels
    ]


@router.get("/explore", response_model=List[ChannelResponse], summary="List public channels")
async def list_public_channels(db: AsyncSession = Depends(get_db)) -> Sequence[ChannelResponse]:
    channel_repo = ChannelRepository(db)
    channels = await channel_repo.list_public()
    return [
        ChannelResponse.model_validate(
            {**ch.__dict__, "is_owner": False, "video_count": 0, "short_count": 0}
        )
        for ch in channels
    ]


@router.post(
    "/preview-plan",
    response_model=ChannelPlan,
    summary="Preview LLM search plan without curating",
    dependencies=[Depends(check_csrf)],
)
async def preview_plan(
    payload: PreviewPlanRequest,
    current_user: User = Depends(get_current_user),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings),
) -> ChannelPlan:
    # Rate limit: 10 per hour per user (FR-31)
    await rate_limiter.check_rate_limit(
        f"preview_plan:{current_user.id}", max_requests=10, window_seconds=3600
    )

    llm = await _get_llm_provider(settings)
    system_prompt = (
        "You are an expert video channel curator. Analyze the user's prompt and produce a typed ChannelPlan "
        "containing search queries, inclusion terms, exclusion terms, duration bounds, and safe search settings. "
        "Respond ONLY with valid JSON conforming to the ChannelPlan schema."
    )
    user_prompt = f"<user_prompt>{payload.prompt}</user_prompt>"

    plan = await llm.generate_structured(system=system_prompt, user=user_prompt, schema=ChannelPlan)
    return plan


@router.get(
    "/by-handle/{handle}", response_model=ChannelResponse, summary="Get channel header by handle"
)
async def get_by_handle(
    handle: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> ChannelResponse:
    channel_repo = ChannelRepository(db)
    user_id = current_user.id if current_user else None
    channel = await channel_repo.get_by_handle_accessible(handle, current_user_id=user_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    is_owner = (current_user is not None) and (channel.owner_id == current_user.id)
    # Hide prompt text from non-owners (FR-40)
    prompt_text = channel.prompt if is_owner else None

    return ChannelResponse.model_validate(
        {
            **channel.__dict__,
            "prompt": prompt_text,
            "is_owner": is_owner,
            "video_count": 0,
            "short_count": 0,
        }
    )


@router.patch(
    "/{id}",
    response_model=ChannelResponse,
    summary="Update channel settings",
    dependencies=[Depends(check_csrf)],
)
async def update_channel(
    id: uuid.UUID,
    payload: ChannelUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChannelResponse:
    channel_repo = ChannelRepository(db)
    channel = await channel_repo.get_by_id_scoped(channel_id=id, owner_id=current_user.id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    updated = await channel_repo.update_channel(
        channel=channel,
        name=payload.name,
        description=payload.description,
        prompt=payload.prompt,
        visibility=payload.visibility,
        banner_style=payload.banner_style,
    )
    return ChannelResponse.model_validate(
        {**updated.__dict__, "is_owner": True, "video_count": 0, "short_count": 0}
    )


@router.delete("/{id}", summary="Delete channel", dependencies=[Depends(check_csrf)])
async def delete_channel(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    channel_repo = ChannelRepository(db)
    channel = await channel_repo.get_by_id_scoped(channel_id=id, owner_id=current_user.id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    await channel_repo.delete_channel(channel)
    return {"status": "deleted"}


@router.get(
    "/{id}/videos", response_model=CursorPage[VideoResponse], summary="Channel Videos / Shorts tab"
)
async def get_channel_videos_tab(
    id: uuid.UUID,
    kind: Optional[str] = Query(None, pattern="^(video|short)$"),
    sort: str = Query("latest", pattern="^(latest|score|views)$"),
    limit: int = 24,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> CursorPage[VideoResponse]:
    channel_repo = ChannelRepository(db)
    video_repo = VideoRepository(db)

    user_id = current_user.id if current_user else None
    # Verify accessibility
    channel = await channel_repo.get_by_id_scoped(id, owner_id=user_id) if user_id else None
    if not channel:
        # Check if unlisted or public
        from sqlalchemy import select

        res = await db.execute(select(Channel).where(Channel.id == id))
        ch = res.scalar_one_or_none()
        if not ch or ch.visibility == "private":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    videos = await channel_repo.get_channel_videos(channel_id=id, kind=kind, sort=sort, limit=limit)
    items = []
    for v in videos:
        is_liked = await video_repo.is_liked_by_user(user_id, v.id) if user_id else False
        items.append(
            VideoResponse.model_validate({**v.__dict__, "is_liked": is_liked, "is_saved": False})
        )

    return CursorPage(items=items, next_cursor=None, has_more=False)


@router.get(
    "/{id}/liked",
    response_model=CursorPage[VideoResponse],
    summary="Videos in channel liked by current user",
)
async def get_channel_liked_tab(
    id: uuid.UUID,
    limit: int = 24,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CursorPage[VideoResponse]:
    channel_repo = ChannelRepository(db)
    videos = await channel_repo.get_channel_liked_videos(
        channel_id=id, user_id=current_user.id, limit=limit
    )
    items = [
        VideoResponse.model_validate({**v.__dict__, "is_liked": True, "is_saved": False})
        for v in videos
    ]
    return CursorPage(items=items, next_cursor=None, has_more=False)


@router.post(
    "/{id}/refresh",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger channel refresh",
    dependencies=[Depends(check_csrf)],
)
async def refresh_channel(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # Rate limit: 1 request per 15 min per channel (FR-34)
    await rate_limiter.check_rate_limit(f"refresh_channel:{id}", max_requests=1, window_seconds=900)

    channel_repo = ChannelRepository(db)
    channel = await channel_repo.get_by_id_scoped(channel_id=id, owner_id=current_user.id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    channel.status = "curating"
    await db.commit()
    return {"status": "enqueued", "job_id": str(uuid.uuid4())}


@router.get("/{id}/status", summary="Poll channel curation status")
async def get_channel_status(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    channel_repo = ChannelRepository(db)
    channel = await channel_repo.get_by_id_scoped(channel_id=id, owner_id=current_user.id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return {"status": channel.status}


@router.post(
    "/{id}/videos", summary="Manually add video to channel", dependencies=[Depends(check_csrf)]
)
async def add_video_manually(
    id: uuid.UUID,
    youtube_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    channel_repo = ChannelRepository(db)
    video_repo = VideoRepository(db)

    channel = await channel_repo.get_by_id_scoped(channel_id=id, owner_id=current_user.id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    video = await video_repo.get_by_youtube_id(youtube_id)
    if not video:
        source = (
            YouTubeDataAPISource(settings.YT_API_KEY) if settings.YT_API_KEY else FakeVideoSource()
        )
        details = await source.get_video_details([youtube_id])
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invalid YouTube video ID"
            )
        item = details[0]
        snippet = item.get("snippet", {})
        video = await video_repo.upsert_video(
            {
                "youtube_id": youtube_id,
                "title": snippet.get("title", "Untitled"),
                "description": snippet.get("description", ""),
                "duration_s": 180,
                "is_short": False,
                "aspect": "landscape",
                "thumbnails": snippet.get("thumbnails", {}),
                "published_at": snippet.get("publishedAt", "2026-01-01T00:00:00Z"),
            }
        )

    await channel_repo.add_manual_video(channel_id=id, video_id=video.id)
    return {"status": "added"}


@router.delete(
    "/{id}/videos/{youtube_id}",
    summary="Remove video and add to exclusions",
    dependencies=[Depends(check_csrf)],
)
async def remove_video_from_channel(
    id: uuid.UUID,
    youtube_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    channel_repo = ChannelRepository(db)
    video_repo = VideoRepository(db)

    channel = await channel_repo.get_by_id_scoped(channel_id=id, owner_id=current_user.id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    video = await video_repo.get_by_youtube_id(youtube_id)
    if video:
        await channel_repo.remove_video_from_channel(channel_id=id, video=video)
    return {"status": "removed_and_excluded"}


@router.patch(
    "/{id}/videos/{youtube_id}", summary="Pin or unpin video", dependencies=[Depends(check_csrf)]
)
async def pin_video(
    id: uuid.UUID,
    youtube_id: str,
    pinned: bool = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    channel_repo = ChannelRepository(db)
    video_repo = VideoRepository(db)

    channel = await channel_repo.get_by_id_scoped(channel_id=id, owner_id=current_user.id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    video = await video_repo.get_by_youtube_id(youtube_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    await channel_repo.pin_video(channel_id=id, video_id=video.id, pinned=pinned)
    return {"status": "updated_pin"}


@router.get("/{id}/runs", summary="Get curation history runs (owner only)")
async def get_curation_runs(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Sequence[dict]:
    channel_repo = ChannelRepository(db)
    channel = await channel_repo.get_by_id_scoped(channel_id=id, owner_id=current_user.id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    runs = await channel_repo.get_curation_runs(channel_id=id, limit=10)
    return [
        {
            "id": str(r.id),
            "trigger": r.trigger,
            "queries": r.queries,
            "candidates": r.candidates,
            "selected": r.selected,
            "llm_provider": r.llm_provider,
            "yt_units": r.yt_units,
            "duration_ms": r.duration_ms,
            "status": r.status,
            "error": r.error,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]
