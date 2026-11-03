"""Video repository."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import delete, desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import CategoryVideo
from app.models.video import HiddenVideo, Like, Video, WatchHistory


class VideoRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_youtube_id(self, youtube_id: str) -> Optional[Video]:
        stmt = select(Video).where(Video.youtube_id == youtube_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def upsert_video(self, video_data: Dict[str, Any]) -> Video:
        stmt = (
            insert(Video)
            .values(**video_data)
            .on_conflict_do_update(
                index_elements=["youtube_id"],
                set_={
                    "title": video_data.get("title"),
                    "description": video_data.get("description"),
                    "duration_s": video_data.get("duration_s"),
                    "is_short": video_data.get("is_short"),
                    "thumbnails": video_data.get("thumbnails"),
                    "view_count": video_data.get("view_count"),
                    "like_count": video_data.get("like_count"),
                    "fetched_at": datetime.now(timezone.utc),
                },
            )
            .returning(Video)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one()

    async def is_liked_by_user(self, user_id: uuid.UUID, video_id: uuid.UUID) -> bool:
        stmt = select(Like).where(Like.user_id == user_id, Like.video_id == video_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def like_video(self, user_id: uuid.UUID, video_id: uuid.UUID) -> None:
        stmt = insert(Like).values(user_id=user_id, video_id=video_id).on_conflict_do_nothing()
        await self.db.execute(stmt)
        await self.db.commit()

    async def unlike_video(self, user_id: uuid.UUID, video_id: uuid.UUID) -> None:
        stmt = delete(Like).where(Like.user_id == user_id, Like.video_id == video_id)
        await self.db.execute(stmt)
        await self.db.commit()

    async def hide_video(self, user_id: uuid.UUID, video_id: uuid.UUID) -> None:
        stmt = (
            insert(HiddenVideo).values(user_id=user_id, video_id=video_id).on_conflict_do_nothing()
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_progress(
        self, user_id: uuid.UUID, video_id: uuid.UUID, progress_s: int
    ) -> None:
        stmt = (
            insert(WatchHistory)
            .values(
                user_id=user_id,
                video_id=video_id,
                progress_s=progress_s,
                last_watched_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=["user_id", "video_id"],
                set_={
                    "progress_s": progress_s,
                    "last_watched_at": datetime.now(timezone.utc),
                },
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_user_likes(self, user_id: uuid.UUID, limit: int = 24) -> Sequence[Video]:
        stmt = (
            select(Video)
            .join(Like, Video.id == Like.video_id)
            .where(Like.user_id == user_id)
            .order_by(desc(Like.created_at))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_category_videos(self, category_id: uuid.UUID, limit: int = 12) -> Sequence[Video]:
        stmt = (
            select(Video)
            .join(CategoryVideo, Video.id == CategoryVideo.video_id)
            .where(CategoryVideo.category_id == category_id)
            .order_by(CategoryVideo.rank)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_continue_watching(self, user_id: uuid.UUID, limit: int = 10) -> Sequence[Video]:
        stmt = (
            select(Video)
            .join(WatchHistory, Video.id == WatchHistory.video_id)
            .where(
                WatchHistory.user_id == user_id,
                WatchHistory.progress_s > 0,
                Video.duration_s > 0,
                # Progress between 5% and 90% (FR-53)
                (WatchHistory.progress_s * 100 / Video.duration_s).between(5, 90),
            )
            .order_by(desc(WatchHistory.last_watched_at))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def search_local(self, query: str, limit: int = 30) -> Sequence[Video]:
        """PostgreSQL full-text search using tsvector + trgm."""
        clean_q = " & ".join(query.strip().split())
        stmt = (
            select(Video)
            .where(
                Video.search_tsv.op("@@")(func.to_tsquery("english", clean_q))
                | Video.title.ilike(f"%{query}%")
            )
            .order_by(desc(Video.published_at))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()
