"""Pytest fixtures for unit and integration testing."""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.deps import get_db, get_redis
from app.main import create_app
from app.models.base import Base


class MockPipeline:
    def __init__(self, redis: "MockRedis"):
        self.redis = redis

    def zremrangebyscore(self, key: str, min_s: float, max_s: float):
        return self

    def zadd(self, key: str, mapping: dict):
        if key not in self.redis.zsets:
            self.redis.zsets[key] = []
        for _, score in mapping.items():
            self.redis.zsets[key].append(score)
        return self

    def zcard(self, key: str):
        return self

    def expire(self, key: str, seconds: int):
        return self

    async def execute(self):
        count = sum(len(v) for v in self.redis.zsets.values()) or 1
        return [0, 1, count, True]


class MockRedis:
    """In-memory mock for Redis session & rate-limiting."""

    def __init__(self):
        self.store = {}
        self.sets = {}
        self.zsets = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value
        return True

    async def delete(self, key: str):
        self.store.pop(key, None)
        self.sets.pop(key, None)
        self.zsets.pop(key, None)
        return True

    async def expire(self, key: str, seconds: int):
        return True

    async def sadd(self, key: str, member: str):
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].add(member)
        return 1

    async def smembers(self, key: str):
        return self.sets.get(key, set())

    async def srem(self, key: str, member: str):
        if key in self.sets:
            self.sets[key].discard(member)
        return 1

    def pipeline(self):
        return MockPipeline(self)

    async def ping(self):
        return True

    async def close(self):
        pass


@pytest.fixture
def mock_redis():
    return MockRedis()


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        APP_ENV="test",
        ALLOWED_EMAILS="testuser@example.com,vajapravin23@gmail.com",
        OPEN_REGISTRATION=False,
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
    )


@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(
    test_db: AsyncSession, mock_redis: MockRedis, test_settings: Settings
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_db():
        yield test_db

    async def override_get_redis():
        yield mock_redis

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
