"""Channel repository with strict owner_id scoping."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from sqlalchemy import delete, desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import (
    Channel,
    ChannelCategory,
    ChannelCurationRun,
    ChannelExclusion,
    ChannelVideo,
)
from app.models.video import Like, Video


class ChannelRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id_scoped(
        self, channel_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Optional[Channel]:
        """Fetch channel strictly verifying ownership."""
        stmt = select(Channel).where(Channel.id == channel_id, Channel.owner_id == owner_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_handle_accessible(
        self,
        handle: str,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> Optional[Channel]:
        """Fetch channel by handle respecting visibility rules (FR-44).

        - Private: accessible only if owner_id == current_user_id (otherwise returns None -> 404)
        - Unlisted / Public: accessible to any authenticated user
        """
        stmt = select(Channel).where(Channel.handle == handle)
        res = await self.db.execute(stmt)
        channel = res.scalar_one_or_none()
        if not channel:
            return None
        if channel.visibility == "private":
            if not current_user_id or channel.owner_id != current_user_id:
                return None  # Return 404, not 403 (SEC-04 / FR-44)
        return channel

    async def list_by_owner(self, owner_id: uuid.UUID) -> Sequence[Channel]:
        stmt = (
            select(Channel).where(Channel.owner_id == owner_id).order_by(desc(Channel.created_at))
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def list_public(self, limit: int = 50) -> Sequence[Channel]:
        stmt = (
            select(Channel)
            .where(Channel.visibility == "public")
            .order_by(desc(Channel.created_at))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def create_channel(
        self,
        owner_id: uuid.UUID,
        name: str,
        handle: str,
        prompt: str,
        description: Optional[str] = None,
        visibility: str = "private",
        banner_style: Optional[str] = None,
        category_ids: Optional[List[uuid.UUID]] = None,
    ) -> Channel:
        channel = Channel(
            owner_id=owner_id,
            name=name,
            handle=handle,
            description=description,
            prompt=prompt,
            visibility=visibility,
            banner_style=banner_style,
            status="curating",
        )
        self.db.add(channel)
        await self.db.flush()

        if category_ids:
            for cat_id in category_ids:
                self.db.add(ChannelCategory(channel_id=channel.id, category_id=cat_id))

        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def update_channel(
        self,
        channel: Channel,
        name: Optional[str] = None,
        description: Optional[str] = None,
        prompt: Optional[str] = None,
        visibility: Optional[str] = None,
        banner_style: Optional[str] = None,
    ) -> Channel:
        if name is not None:
            channel.name = name
        if description is not None:
            channel.description = description
        if prompt is not None:
            channel.prompt = prompt
        if visibility is not None:
            channel.visibility = visibility
        if banner_style is not None:
            channel.banner_style = banner_style

        channel.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def delete_channel(self, channel: Channel) -> None:
        await self.db.delete(channel)
        await self.db.commit()

    async def get_channel_videos(
        self,
        channel_id: uuid.UUID,
        kind: Optional[str] = None,
        sort: str = "latest",
        limit: int = 24,
    ) -> Sequence[Video]:
        stmt = (
            select(Video)
            .join(ChannelVideo, Video.id == ChannelVideo.video_id)
            .where(ChannelVideo.channel_id == channel_id)
        )
        if kind in ("video", "short"):
            stmt = stmt.where(ChannelVideo.kind == kind)

        # Pinned videos always appear first (FR-41)
        order_clauses = [desc(ChannelVideo.pinned)]
        if sort == "score":
            order_clauses.append(desc(ChannelVideo.score))
        elif sort == "views":
            order_clauses.append(desc(Video.view_count))
        else:  # default latest
            order_clauses.append(desc(ChannelVideo.added_at))

        stmt = stmt.order_by(*order_clauses).limit(limit)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_channel_liked_videos(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 24,
    ) -> Sequence[Video]:
        """Fetch videos from this channel liked by current user (FR-43 / A3)."""
        stmt = (
            select(Video)
            .join(ChannelVideo, Video.id == ChannelVideo.video_id)
            .join(Like, Video.id == Like.video_id)
            .where(ChannelVideo.channel_id == channel_id, Like.user_id == user_id)
            .order_by(desc(Like.created_at))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def add_manual_video(
        self,
        channel_id: uuid.UUID,
        video_id: uuid.UUID,
        kind: str = "video",
    ) -> None:
        stmt = (
            insert(ChannelVideo)
            .values(
                channel_id=channel_id,
                video_id=video_id,
                kind=kind,
                score=100,
                source="manual",
                pinned=False,
            )
            .on_conflict_do_nothing()
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def remove_video_from_channel(
        self,
        channel_id: uuid.UUID,
        video: Video,
    ) -> None:
        # Delete from channel_videos
        await self.db.execute(
            delete(ChannelVideo).where(
                ChannelVideo.channel_id == channel_id,
                ChannelVideo.video_id == video.id,
            )
        )
        # Record into channel_exclusions so refresh never brings it back (FR-35)
        stmt = (
            insert(ChannelExclusion)
            .values(channel_id=channel_id, youtube_id=video.youtube_id)
            .on_conflict_do_nothing()
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def pin_video(
        self,
        channel_id: uuid.UUID,
        video_id: uuid.UUID,
        pinned: bool,
    ) -> None:
        stmt = (
            insert(ChannelVideo)
            .values(channel_id=channel_id, video_id=video_id, pinned=pinned)
            .on_conflict_do_update(
                index_elements=["channel_id", "video_id"],
                set_={"pinned": pinned},
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_curation_runs(
        self,
        channel_id: uuid.UUID,
        limit: int = 10,
    ) -> Sequence[ChannelCurationRun]:
        stmt = (
            select(ChannelCurationRun)
            .where(ChannelCurationRun.channel_id == channel_id)
            .order_by(desc(ChannelCurationRun.created_at))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()
