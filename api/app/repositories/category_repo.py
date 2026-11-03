"""Category repository."""

import uuid
from typing import List, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, UserInterest


class CategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(self) -> Sequence[Category]:
        stmt = select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_by_slug(self, slug: str) -> Category | None:
        stmt = select(Category).where(Category.slug == slug, Category.is_active.is_(True))
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_interests(self, user_id: uuid.UUID) -> Sequence[Category]:
        stmt = (
            select(Category)
            .join(UserInterest, Category.id == UserInterest.category_id)
            .where(UserInterest.user_id == user_id, Category.is_active.is_(True))
            .order_by(UserInterest.position)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def set_user_interests(self, user_id: uuid.UUID, category_ids: List[uuid.UUID]) -> None:
        # Clear existing interests
        await self.db.execute(delete(UserInterest).where(UserInterest.user_id == user_id))
        # Insert new interests with position
        for idx, cat_id in enumerate(category_ids):
            interest = UserInterest(user_id=user_id, category_id=cat_id, position=idx)
            self.db.add(interest)
        await self.db.commit()
