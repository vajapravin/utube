"""Redis-backed session management using 256-bit opaque tokens."""

import json
import secrets
import uuid
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

COOKIE_NAME = "__Host-mytube_sid"
SLIDING_TTL_SECONDS = 30 * 24 * 3600  # 30 days
ABSOLUTE_TTL_SECONDS = 90 * 24 * 3600  # 90 days


class SessionManager:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self.redis = redis_client

    def _session_key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _user_sessions_key(self, user_id: uuid.UUID) -> str:
        return f"user_sessions:{user_id}"

    async def create_session(self, user_id: uuid.UUID, email: str, role: str) -> str:
        session_id = secrets.token_urlsafe(32)
        key = self._session_key(session_id)
        data = {
            "session_id": session_id,
            "user_id": str(user_id),
            "email": email,
            "role": role,
            "created_at": secrets.token_hex(4),
        }
        # Store session with 30-day sliding TTL
        await self.redis.set(key, json.dumps(data), ex=SLIDING_TTL_SECONDS)
        # Add to user's set of active sessions
        await self.redis.sadd(self._user_sessions_key(user_id), session_id)
        await self.redis.expire(self._user_sessions_key(user_id), ABSOLUTE_TTL_SECONDS)
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        key = self._session_key(session_id)
        raw = await self.redis.get(key)
        if not raw:
            return None
        # Slide TTL forward
        await self.redis.expire(key, SLIDING_TTL_SECONDS)
        return json.loads(raw)

    async def delete_session(self, session_id: str) -> None:
        key = self._session_key(session_id)
        raw = await self.redis.get(key)
        if raw:
            data = json.loads(raw)
            user_id = data.get("user_id")
            if user_id:
                await self.redis.srem(self._user_sessions_key(uuid.UUID(user_id)), session_id)
            await self.redis.delete(key)

    async def delete_all_user_sessions(self, user_id: uuid.UUID) -> None:
        u_key = self._user_sessions_key(user_id)
        sessions = await self.redis.smembers(u_key)
        for s in sessions:
            sid = s.decode("utf-8") if isinstance(s, bytes) else s
            await self.redis.delete(self._session_key(sid))
        await self.redis.delete(u_key)
