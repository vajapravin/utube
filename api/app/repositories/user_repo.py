"""User repository."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_google_sub(self, sub: str) -> Optional[User]:
        stmt = select(User).where(User.google_sub == sub, User.deleted_at.is_(None))
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def upsert_from_google(
        self,
        sub: str,
        email: str,
        display_name: str,
        avatar_url: Optional[str] = None,
    ) -> tuple[User, bool]:
        """Upsert user on Google OIDC login.

        Returns (user, is_new).
        """
        existing = await self.get_by_google_sub(sub)
        if existing:
            existing.email = email.lower()
            existing.display_name = display_name
            existing.avatar_url = avatar_url
            existing.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing, False

        new_user = User(
            google_sub=sub,
            email=email.lower(),
            display_name=display_name,
            avatar_url=avatar_url,
            role="user",
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user, True

    async def update_settings(self, user: User, settings: Dict[str, Any]) -> User:
        updated = dict(user.settings)
        updated.update({k: v for k, v in settings.items() if v is not None})
        user.settings = updated
        user.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def complete_onboarding(self, user: User) -> User:
        user.onboarded_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def soft_delete(self, user: User) -> None:
        user.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()
