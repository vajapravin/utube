"""FastAPI dependencies: Database sessions, Redis clients, and Authenticated User context."""

import uuid
from typing import AsyncGenerator, Optional

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import Depends, HTTPException, Request, status
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.models.user import User
from app.security.csrf import verify_csrf
from app.security.rate_limit import RateLimiter
from app.security.sessions import COOKIE_NAME, DEV_COOKIE_NAME, SessionManager

# Async Engine, SessionMaker, and Arq Redis singletons
_engine = None
_sessionmaker = None
_redis = None
_arq_pool = None


def get_engine(settings: Settings = Depends(get_settings)):
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=10,
            max_overflow=5,
        )
    return _engine


def get_sessionmaker(settings: Settings = Depends(get_settings)):
    global _sessionmaker
    if _sessionmaker is None:
        engine = get_engine(settings)
        _sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    return _sessionmaker


async def get_db(settings: Settings = Depends(get_settings)) -> AsyncGenerator[AsyncSession, None]:
    sm = get_sessionmaker(settings)
    async with sm() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_redis(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[aioredis.Redis, None]:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    yield _redis


async def get_rate_limiter(redis: aioredis.Redis = Depends(get_redis)) -> RateLimiter:
    return RateLimiter(redis)


async def get_session_manager(redis: aioredis.Redis = Depends(get_redis)) -> SessionManager:
    return SessionManager(redis)


async def get_arq_pool(settings: Settings = Depends(get_settings)) -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool


async def get_current_user_optional(
    request: Request,
    session_mgr: SessionManager = Depends(get_session_manager),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    session_id = request.cookies.get(COOKIE_NAME) or request.cookies.get(DEV_COOKIE_NAME)
    if not session_id:
        return None
    session_data = await session_mgr.get_session(session_id)
    if not session_data:
        return None
    user_id = session_data.get("user_id")
    if not user_id:
        return None

    user = await db.get(User, uuid.UUID(user_id))
    if not user or user.deleted_at is not None:
        return None
    return user


async def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user


async def check_csrf(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    verify_csrf(request, settings.PUBLIC_BASE_URL)
