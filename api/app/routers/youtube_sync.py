"""YouTube integration & Google Takeout sync router."""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from redis import asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.deps import check_csrf, get_current_user, get_db, get_redis
from app.models.playlist import Playlist, PlaylistItem
from app.models.user import User
from app.models.video import Like, Video, WatchHistory
from app.providers.video_source import FakeVideoSource, YouTubeDataAPISource
from app.repositories.video_repo import VideoRepository
from mytube_shared.guardrails import evaluate_career_relevance, is_entertainment_or_clickbait

router = APIRouter(prefix="/youtube", tags=["YouTube Integration"])


def _parse_iso_duration(duration_str: str) -> int:
    if not duration_str:
        return 0
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


def _extract_playlist_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()
    if "list=" in url_or_id:
        match = re.search(r"list=([a-zA-Z0-9_-]+)", url_or_id)
        if match:
            return match.group(1)
    return url_or_id


async def _get_video_source(settings: Settings) -> YouTubeDataAPISource | FakeVideoSource:
    if settings.VIDEO_SOURCE == "fake":
        return FakeVideoSource()
    return YouTubeDataAPISource(api_key=settings.YT_API_KEY)


async def _get_user_tokens(redis_client: aioredis.Redis, user_id: uuid.UUID) -> Optional[Dict[str, str]]:
    raw = await redis_client.get(f"google_oauth:{user_id}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


class ImportPlaylistRequest(BaseModel):
    url_or_id: str
    title: Optional[str] = None


@router.get("/status", summary="Check YouTube OAuth sync status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> Dict[str, Any]:
    tokens = await _get_user_tokens(redis_client, current_user.id)
    return {
        "connected": tokens is not None and bool(tokens.get("access_token")),
        "has_refresh_token": tokens is not None and bool(tokens.get("refresh_token")),
    }


@router.post("/sync/liked", summary="Sync user's liked videos from YouTube", dependencies=[Depends(check_csrf)])
async def sync_liked_videos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    tokens = await _get_user_tokens(redis_client, current_user.id)
    if not tokens or not tokens.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YouTube is not connected. Please connect your YouTube account via Google OAuth first.",
        )

    source = await _get_video_source(settings)
    liked_items = await source.get_liked_videos(access_token=tokens["access_token"], max_results=50)

    video_repo = VideoRepository(db)
    synced_count = 0

    for item in liked_items:
        yt_id = item.get("id")
        if isinstance(yt_id, dict):
            yt_id = yt_id.get("videoId")
        if not yt_id:
            continue

        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})
        statistics = item.get("statistics", {})

        duration_s = _parse_iso_duration(content_details.get("duration", "PT3M")) or 180
        is_short = duration_s <= settings.SHORTS_MAX_SECONDS

        video = await video_repo.upsert_video({
            "youtube_id": yt_id,
            "title": snippet.get("title", "Untitled"),
            "description": snippet.get("description", ""),
            "source_channel_id": snippet.get("channelId"),
            "source_channel_title": snippet.get("channelTitle"),
            "duration_s": duration_s,
            "is_short": is_short,
            "aspect": "vertical" if is_short else "landscape",
            "thumbnails": snippet.get("thumbnails", {}),
            "published_at": snippet.get("publishedAt", datetime.now(timezone.utc).isoformat()),
            "view_count": int(statistics.get("viewCount", 0)),
            "like_count": int(statistics.get("likeCount", 0)),
        })

        await video_repo.like_video(current_user.id, video.id)
        synced_count += 1

    return {
        "status": "success",
        "synced_count": synced_count,
        "message": f"Successfully synced {synced_count} liked videos from YouTube.",
    }


@router.post("/sync/playlists", summary="Sync user's YouTube playlists", dependencies=[Depends(check_csrf)])
async def sync_user_playlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    tokens = await _get_user_tokens(redis_client, current_user.id)
    if not tokens or not tokens.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YouTube is not connected. Please connect your YouTube account via Google OAuth first.",
        )

    source = await _get_video_source(settings)
    playlists_raw = await source.get_my_playlists(access_token=tokens["access_token"], max_results=25)

    video_repo = VideoRepository(db)
    playlists_created = 0
    total_videos_synced = 0

    for pl in playlists_raw:
        yt_pl_id = pl.get("id")
        snippet = pl.get("snippet", {})
        title = snippet.get("title") or "YouTube Playlist"
        desc = snippet.get("description", "")

        # Find or create playlist
        stmt = select(Playlist).where(
            Playlist.owner_id == current_user.id,
            Playlist.title == title,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if not existing:
            existing = Playlist(
                id=uuid.uuid4(),
                owner_id=current_user.id,
                title=title,
                description=desc[:500] if desc else None,
                visibility="private",
            )
            db.add(existing)
            await db.commit()
            playlists_created += 1

        # Fetch playlist items
        items = await source.get_playlist_items(
            playlist_id=yt_pl_id,
            access_token=tokens["access_token"],
            max_results=50,
        )

        pos_idx = 1000
        for item in items:
            item_snippet = item.get("snippet", {})
            res_id = item_snippet.get("resourceId", {})
            yt_id = res_id.get("videoId")
            if not yt_id:
                continue

            video = await video_repo.upsert_video({
                "youtube_id": yt_id,
                "title": item_snippet.get("title", "Untitled"),
                "description": item_snippet.get("description", ""),
                "source_channel_id": item_snippet.get("channelId"),
                "source_channel_title": item_snippet.get("channelTitle"),
                "duration_s": 180,
                "is_short": False,
                "aspect": "landscape",
                "thumbnails": item_snippet.get("thumbnails", {}),
                "published_at": item_snippet.get("publishedAt", datetime.now(timezone.utc).isoformat()),
            })

            # Add to playlist_items
            item_stmt = (
                insert(PlaylistItem)
                .values(
                    id=uuid.uuid4(),
                    playlist_id=existing.id,
                    video_id=video.id,
                    position=f"{pos_idx:06d}",
                    added_at=datetime.now(timezone.utc),
                )
                .on_conflict_do_nothing()
            )
            await db.execute(item_stmt)
            pos_idx += 1000
            total_videos_synced += 1

        await db.commit()

    return {
        "status": "success",
        "playlists_synced": len(playlists_raw),
        "total_videos_synced": total_videos_synced,
    }


@router.post("/import-playlist", summary="Import any public YouTube playlist by URL or ID", dependencies=[Depends(check_csrf)])
async def import_public_playlist(
    payload: ImportPlaylistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    playlist_id = _extract_playlist_id(payload.url_or_id)
    if not playlist_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube playlist URL or ID")

    source = await _get_video_source(settings)
    items = await source.get_playlist_items(playlist_id=playlist_id, max_results=50)
    if not items:
        raise HTTPException(status_code=404, detail="No videos found in this YouTube playlist or playlist is private.")

    title = payload.title or f"Imported Playlist ({playlist_id[:8]})"
    pl = Playlist(
        id=uuid.uuid4(),
        owner_id=current_user.id,
        title=title,
        description=f"Imported from YouTube playlist {playlist_id}",
        visibility="private",
    )
    db.add(pl)
    await db.commit()

    video_repo = VideoRepository(db)
    pos = 1000
    added = 0
    for it in items:
        s = it.get("snippet", {})
        vid_id = s.get("resourceId", {}).get("videoId")
        if not vid_id:
            continue
        v = await video_repo.upsert_video({
            "youtube_id": vid_id,
            "title": s.get("title", "Untitled"),
            "description": s.get("description", ""),
            "source_channel_id": s.get("channelId"),
            "source_channel_title": s.get("channelTitle"),
            "duration_s": 180,
            "is_short": False,
            "aspect": "landscape",
            "thumbnails": s.get("thumbnails", {}),
            "published_at": s.get("publishedAt", datetime.now(timezone.utc).isoformat()),
        })
        item_stmt = (
            insert(PlaylistItem)
            .values(
                id=uuid.uuid4(),
                playlist_id=pl.id,
                video_id=v.id,
                position=f"{pos:06d}",
                added_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_nothing()
        )
        await db.execute(item_stmt)
        pos += 1000
        added += 1

    await db.commit()
    return {
        "status": "success",
        "playlist_id": str(pl.id),
        "title": pl.title,
        "items_count": added,
    }


@router.post("/sync/takeout-history", summary="Import Google Takeout watch-history.json", dependencies=[Depends(check_csrf)])
async def import_takeout_history(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    content = await file.read()
    try:
        data = json.loads(content.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {exc}")

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Expected a JSON array of watch history items.")

    video_repo = VideoRepository(db)
    imported_count = 0
    candidate_ids = []
    history_records = []

    for entry in data[:300]:  # Limit to 300 most recent items to avoid quota overload
        title_url = entry.get("titleUrl", "")
        if not title_url or "watch?v=" not in title_url:
            continue
        yt_id = title_url.split("watch?v=")[-1].split("&")[0]
        if not yt_id or len(yt_id) != 11:
            continue

        title = entry.get("title", "").replace("Watched ", "")
        subs = entry.get("subtitles", [])
        channel_title = subs[0].get("name") if subs else "YouTube Creator"
        channel_id = subs[0].get("url", "").split("/")[-1] if subs else None
        watched_time_str = entry.get("time")

        try:
            watched_at = datetime.fromisoformat(watched_time_str.replace("Z", "+00:00")) if watched_time_str else datetime.now(timezone.utc)
        except Exception:
            watched_at = datetime.now(timezone.utc)

        # Check guardrails: reject entertainment / meme spam if configured
        if is_entertainment_or_clickbait(title, ""):
            continue

        video = await video_repo.upsert_video({
            "youtube_id": yt_id,
            "title": title or "Watched Video",
            "description": f"Imported from Google Takeout. Channel: {channel_title}",
            "source_channel_id": channel_id,
            "source_channel_title": channel_title,
            "duration_s": 300,
            "is_short": False,
            "aspect": "landscape",
            "thumbnails": {"high": {"url": f"https://i.ytimg.com/vi/{yt_id}/hqdefault.jpg"}},
            "published_at": watched_at,
        })

        # Record in watch history
        hist_stmt = (
            insert(WatchHistory)
            .values(
                user_id=current_user.id,
                video_id=video.id,
                progress_s=300,
                last_watched_at=watched_at,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "video_id"],
                set_={"last_watched_at": watched_at},
            )
        )
        await db.execute(hist_stmt)
        imported_count += 1

    await db.commit()
    return {
        "status": "success",
        "imported_count": imported_count,
        "message": f"Successfully imported {imported_count} learning videos into your watch history.",
    }
