"""Playlists router: CRUD, items management, and Lexorank reordering."""

import uuid
from typing import List, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import check_csrf, get_current_user, get_db
from app.models.user import User
from app.models.video import Video
from app.repositories.playlist_repo import PlaylistRepository
from app.repositories.video_repo import VideoRepository
from app.schemas.playlist import (
    PlaylistCreate,
    PlaylistItemAdd,
    PlaylistItemMove,
    PlaylistItemResponse,
    PlaylistResponse,
    PlaylistUpdate,
)
from app.schemas.video import VideoResponse

router = APIRouter(prefix="/playlists", tags=["Playlists"])


@router.post(
    "",
    response_model=PlaylistResponse,
    summary="Create a new playlist",
    dependencies=[Depends(check_csrf)],
)
async def create_playlist(
    payload: PlaylistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    repo = PlaylistRepository(db)
    pl = await repo.create_playlist(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        visibility=payload.visibility,
    )
    return PlaylistResponse.model_validate(pl)


@router.get("", response_model=List[PlaylistResponse], summary="List user's playlists")
async def list_playlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Sequence[PlaylistResponse]:
    repo = PlaylistRepository(db)
    # Ensure Watch later exists (FR-60)
    await repo.get_or_create_watch_later(current_user.id)
    playlists = await repo.list_by_owner(current_user.id)
    return [PlaylistResponse.model_validate(p) for p in playlists]


@router.get("/{id}", summary="Get playlist header and items")
async def get_playlist(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = PlaylistRepository(db)
    playlist = await repo.get_by_id_accessible(id, current_user_id=current_user.id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

    items = await repo.get_items(id)
    item_responses = [
        PlaylistItemResponse(
            id=item.id,
            position=item.position,
            added_at=item.added_at,
            video=VideoResponse.model_validate({**v.__dict__, "is_liked": False, "is_saved": True}),
        )
        for item, v in items
    ]

    return {
        "playlist": PlaylistResponse.model_validate(playlist),
        "items": item_responses,
    }


@router.patch(
    "/{id}",
    response_model=PlaylistResponse,
    summary="Update playlist",
    dependencies=[Depends(check_csrf)],
)
async def update_playlist(
    id: uuid.UUID,
    payload: PlaylistUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    repo = PlaylistRepository(db)
    playlist = await repo.get_by_id_scoped(id, owner_id=current_user.id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

    updated = await repo.update_playlist(
        playlist=playlist,
        title=payload.title,
        description=payload.description,
        visibility=payload.visibility,
    )
    return PlaylistResponse.model_validate(updated)


@router.delete("/{id}", summary="Delete playlist", dependencies=[Depends(check_csrf)])
async def delete_playlist(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    repo = PlaylistRepository(db)
    playlist = await repo.get_by_id_scoped(id, owner_id=current_user.id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

    try:
        await repo.delete_playlist(playlist)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {"status": "deleted"}


@router.post(
    "/{id}/items",
    response_model=PlaylistItemResponse,
    summary="Add video to playlist",
    dependencies=[Depends(check_csrf)],
)
async def add_item(
    id: uuid.UUID,
    payload: PlaylistItemAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistItemResponse:
    playlist_repo = PlaylistRepository(db)
    video_repo = VideoRepository(db)

    playlist = await playlist_repo.get_by_id_scoped(id, owner_id=current_user.id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

    video = await video_repo.get_by_youtube_id(payload.youtube_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found in catalogue"
        )

    try:
        item = await playlist_repo.add_item(playlist_id=id, video_id=video.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return PlaylistItemResponse(
        id=item.id,
        position=item.position,
        added_at=item.added_at,
        video=VideoResponse.model_validate({**video.__dict__, "is_liked": False, "is_saved": True}),
    )


@router.delete(
    "/{id}/items/{item_id}", summary="Remove item from playlist", dependencies=[Depends(check_csrf)]
)
async def remove_item(
    id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    playlist_repo = PlaylistRepository(db)
    playlist = await playlist_repo.get_by_id_scoped(id, owner_id=current_user.id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

    await playlist_repo.remove_item(playlist_id=id, item_id=item_id)
    return {"status": "removed"}


@router.patch(
    "/{id}/items/{item_id}",
    response_model=PlaylistItemResponse,
    summary="Reorder item via Lexorank",
    dependencies=[Depends(check_csrf)],
)
async def move_item(
    id: uuid.UUID,
    item_id: uuid.UUID,
    payload: PlaylistItemMove,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistItemResponse:
    playlist_repo = PlaylistRepository(db)
    video_repo = VideoRepository(db)

    playlist = await playlist_repo.get_by_id_scoped(id, owner_id=current_user.id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

    try:
        updated_item = await playlist_repo.move_item(
            playlist_id=id,
            item_id=item_id,
            prev_pos=payload.prev_position,
            next_pos=payload.next_position,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    video = await video_repo.get_by_youtube_id(str(updated_item.video_id))
    # Fallback to direct fetch
    if not video:
        video = await db.get(Video, updated_item.video_id)

    return PlaylistItemResponse(
        id=updated_item.id,
        position=updated_item.position,
        added_at=updated_item.added_at,
        video=VideoResponse.model_validate({**video.__dict__, "is_liked": False, "is_saved": True}),
    )
