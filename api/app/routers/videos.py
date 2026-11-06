"""Video interactions router: details, like, hide, progress, up-next, saved-in."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.deps import check_csrf, get_current_user, get_db
from app.models.user import User
from app.models.video import Video
from app.providers.video_source import FakeVideoSource, YouTubeDataAPISource
from app.repositories.playlist_repo import PlaylistRepository
from app.repositories.video_repo import VideoRepository
from app.schemas.playlist import PlaylistResponse
from app.schemas.video import ProgressUpdate, VideoResponse
from pydantic import BaseModel


class VideoNoteUpdate(BaseModel):
    content: str

router = APIRouter(prefix="/videos", tags=["Videos"])


async def _get_video_source(settings: Settings) -> YouTubeDataAPISource | FakeVideoSource:
    if settings.VIDEO_SOURCE == "fake":
        return FakeVideoSource()
    return YouTubeDataAPISource(api_key=settings.YT_API_KEY)


@router.get("/{youtube_id}", response_model=VideoResponse, summary="Get video details")
async def get_video(
    youtube_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VideoResponse:
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_youtube_id(youtube_id)

    if not video:
        # Cache miss: fetch from YouTube Data API (FR-50 / A1)
        source = await _get_video_source(settings)
        details = await source.get_video_details([youtube_id])
        if not details:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

        item = details[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        # Parse duration ISO string or use default
        duration_s = 180  # Default fallback
        video_data = {
            "youtube_id": youtube_id,
            "title": snippet.get("title", "Untitled"),
            "description": snippet.get("description", ""),
            "source_channel_id": snippet.get("channelId"),
            "source_channel_title": snippet.get("channelTitle"),
            "duration_s": duration_s,
            "is_short": duration_s <= settings.SHORTS_MAX_SECONDS,
            "aspect": "vertical" if duration_s <= settings.SHORTS_MAX_SECONDS else "landscape",
            "thumbnails": snippet.get("thumbnails", {}),
            "published_at": snippet.get("publishedAt", "2026-01-01T00:00:00Z"),
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
        }
        video = await video_repo.upsert_video(video_data)

    is_liked = await video_repo.is_liked_by_user(current_user.id, video.id)
    return VideoResponse.model_validate({**video.__dict__, "is_liked": is_liked, "is_saved": False})


@router.get(
    "/{youtube_id}/up-next",
    response_model=List[VideoResponse],
    summary="Get up-next recommendation sidebar",
)
async def get_up_next(
    youtube_id: str,
    channel_id: Optional[uuid.UUID] = Query(None),
    playlist_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[VideoResponse]:
    playlist_repo = PlaylistRepository(db)

    # 1. If playlist_id provided, take next items from playlist (FR-52)
    if playlist_id:
        items = await playlist_repo.get_items(playlist_id)
        vids = [item[1] for item in items if item[1].youtube_id != youtube_id]
        if vids:
            return [
                VideoResponse.model_validate({**v.__dict__, "is_liked": False, "is_saved": False})
                for v in vids[:15]
            ]

    # 2. Fallback to general catalogue recommendations
    from sqlalchemy import select

    stmt = select(Video).where(Video.youtube_id != youtube_id).limit(15)
    res = await db.execute(stmt)
    vids = res.scalars().all()
    return [
        VideoResponse.model_validate({**v.__dict__, "is_liked": False, "is_saved": False})
        for v in vids
    ]


@router.put("/{youtube_id}/like", summary="Like video", dependencies=[Depends(check_csrf)])
async def like_video(
    youtube_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_youtube_id(youtube_id)
    if not video:
        # Preload video
        source = await _get_video_source(settings)
        details = await source.get_video_details([youtube_id])
        if not details:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
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

    await video_repo.like_video(current_user.id, video.id)
    return {"status": "liked"}


@router.delete("/{youtube_id}/like", summary="Unlike video", dependencies=[Depends(check_csrf)])
async def unlike_video(
    youtube_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_youtube_id(youtube_id)
    if video:
        await video_repo.unlike_video(current_user.id, video.id)
    return {"status": "unliked"}


@router.put(
    "/{youtube_id}/hide", summary="Mark video Not Interested", dependencies=[Depends(check_csrf)]
)
async def hide_video(
    youtube_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_youtube_id(youtube_id)
    if video:
        await video_repo.hide_video(current_user.id, video.id)
    return {"status": "hidden"}


@router.put(
    "/{youtube_id}/progress", summary="Record watch progress", dependencies=[Depends(check_csrf)]
)
async def record_progress(
    youtube_id: str,
    payload: ProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if current_user.settings.get("history_paused", False):
        return {"status": "history_paused"}

    video_repo = VideoRepository(db)
    video = await video_repo.get_by_youtube_id(youtube_id)
    if video:
        await video_repo.update_progress(current_user.id, video.id, payload.progress_s)
    return {"status": "progress_saved"}


@router.get(
    "/{youtube_id}/saved-in",
    response_model=List[PlaylistResponse],
    summary="List user playlists containing video",
)
async def get_saved_in(
    youtube_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PlaylistResponse]:
    video_repo = VideoRepository(db)
    playlist_repo = PlaylistRepository(db)

    video = await video_repo.get_by_youtube_id(youtube_id)
    if not video:
        return []

    playlists = await playlist_repo.get_user_playlists_containing_video(current_user.id, video.id)
    return [PlaylistResponse.model_validate(p) for p in playlists]


@router.get("/{youtube_id}/comments", summary="Get top comments for video")
async def get_comments(
    youtube_id: str,
    settings: Settings = Depends(get_settings),
) -> List[dict]:
    source = await _get_video_source(settings)
    return await source.get_comments(youtube_id)


@router.get("/{youtube_id}/notes", summary="Get user's personal study notes for video")
async def get_video_notes(
    youtube_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_youtube_id(youtube_id)
    if not video:
        return {"content": "", "updated_at": None}
    note = await video_repo.get_video_note(current_user.id, video.id)
    if not note:
        return {"content": "", "updated_at": None}
    return {"content": note.content, "updated_at": note.updated_at.isoformat()}


@router.put(
    "/{youtube_id}/notes",
    summary="Save user's personal study notes for video",
    dependencies=[Depends(check_csrf)],
)
async def save_video_notes(
    youtube_id: str,
    payload: VideoNoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_youtube_id(youtube_id)
    if not video:
        source = await _get_video_source(settings)
        details = await source.get_video_details([youtube_id])
        item = details[0] if details else {}
        snippet = item.get("snippet", {})
        video = await video_repo.upsert_video(
            {
                "youtube_id": youtube_id,
                "title": snippet.get("title", "Video"),
                "description": snippet.get("description", ""),
                "duration_s": 180,
                "is_short": False,
                "aspect": "landscape",
                "thumbnails": snippet.get("thumbnails", {}),
                "published_at": snippet.get("publishedAt", "2026-01-01T00:00:00Z"),
            }
        )
    note = await video_repo.upsert_video_note(current_user.id, video.id, payload.content)
    return {"content": note.content, "updated_at": note.updated_at.isoformat()}

