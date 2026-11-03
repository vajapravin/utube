"""Playlist repository with strict owner_id scoping."""

import uuid
from typing import Optional, Sequence

from mytube_shared.lexorank import get_rank_between
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playlist import Playlist, PlaylistItem
from app.models.video import Video


class PlaylistRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id_scoped(
        self, playlist_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Optional[Playlist]:
        """Fetch playlist verifying ownership."""
        stmt = select(Playlist).where(Playlist.id == playlist_id, Playlist.owner_id == owner_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_id_accessible(
        self,
        playlist_id: uuid.UUID,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> Optional[Playlist]:
        """Fetch playlist checking visibility (private only accessible by owner)."""
        stmt = select(Playlist).where(Playlist.id == playlist_id)
        res = await self.db.execute(stmt)
        playlist = res.scalar_one_or_none()
        if not playlist:
            return None
        if playlist.visibility == "private":
            if not current_user_id or playlist.owner_id != current_user_id:
                return None  # 404 to non-owners
        return playlist

    async def list_by_owner(self, owner_id: uuid.UUID) -> Sequence[Playlist]:
        stmt = (
            select(Playlist)
            .where(Playlist.owner_id == owner_id)
            .order_by(desc(Playlist.created_at))
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_or_create_watch_later(self, owner_id: uuid.UUID) -> Playlist:
        """Get or automatically create non-deletable 'Watch later' playlist (FR-60)."""
        stmt = select(Playlist).where(
            Playlist.owner_id == owner_id, Playlist.system_kind == "watch_later"
        )
        res = await self.db.execute(stmt)
        wl = res.scalar_one_or_none()
        if wl:
            return wl

        wl = Playlist(
            owner_id=owner_id,
            title="Watch later",
            description="Videos saved to watch later",
            visibility="private",
            system_kind="watch_later",
        )
        self.db.add(wl)
        await self.db.commit()
        await self.db.refresh(wl)
        return wl

    async def create_playlist(
        self,
        owner_id: uuid.UUID,
        title: str,
        description: Optional[str] = None,
        visibility: str = "private",
    ) -> Playlist:
        playlist = Playlist(
            owner_id=owner_id,
            title=title,
            description=description,
            visibility=visibility,
        )
        self.db.add(playlist)
        await self.db.commit()
        await self.db.refresh(playlist)
        return playlist

    async def update_playlist(
        self,
        playlist: Playlist,
        title: Optional[str] = None,
        description: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> Playlist:
        if title is not None:
            playlist.title = title
        if description is not None:
            playlist.description = description
        if visibility is not None:
            playlist.visibility = visibility
        await self.db.commit()
        await self.db.refresh(playlist)
        return playlist

    async def delete_playlist(self, playlist: Playlist) -> None:
        if playlist.system_kind == "watch_later":
            raise ValueError("The built-in Watch later playlist cannot be deleted")
        await self.db.delete(playlist)
        await self.db.commit()

    async def get_items(self, playlist_id: uuid.UUID) -> Sequence[tuple[PlaylistItem, Video]]:
        stmt = (
            select(PlaylistItem, Video)
            .join(Video, PlaylistItem.video_id == Video.id)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position)
        )
        res = await self.db.execute(stmt)
        return res.all()

    async def add_item(self, playlist_id: uuid.UUID, video_id: uuid.UUID) -> PlaylistItem:
        # Check duplicate
        stmt = select(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.video_id == video_id,
        )
        existing = await self.db.execute(stmt)
        if existing.scalar_one_or_none():
            raise ValueError("Already in playlist")

        # Get last position
        pos_stmt = (
            select(PlaylistItem.position)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(desc(PlaylistItem.position))
            .limit(1)
        )
        last_pos = (await self.db.execute(pos_stmt)).scalar_one_or_none()
        new_pos = get_rank_between(last_pos, None)

        item = PlaylistItem(
            playlist_id=playlist_id,
            video_id=video_id,
            position=new_pos,
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def remove_item(self, playlist_id: uuid.UUID, item_id: uuid.UUID) -> None:
        stmt = delete(PlaylistItem).where(
            PlaylistItem.id == item_id,
            PlaylistItem.playlist_id == playlist_id,
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def move_item(
        self,
        playlist_id: uuid.UUID,
        item_id: uuid.UUID,
        prev_pos: Optional[str],
        next_pos: Optional[str],
    ) -> PlaylistItem:
        stmt = select(PlaylistItem).where(
            PlaylistItem.id == item_id,
            PlaylistItem.playlist_id == playlist_id,
        )
        item = (await self.db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise ValueError("Playlist item not found")

        item.position = get_rank_between(prev_pos, next_pos)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def get_user_playlists_containing_video(
        self,
        owner_id: uuid.UUID,
        video_id: uuid.UUID,
    ) -> Sequence[Playlist]:
        stmt = (
            select(Playlist)
            .join(PlaylistItem, Playlist.id == PlaylistItem.playlist_id)
            .where(Playlist.owner_id == owner_id, PlaylistItem.video_id == video_id)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()
