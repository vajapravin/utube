"""Sliding-window rate limiter using Redis sorted sets."""

import time

import redis.asyncio as aioredis
from fastapi import HTTPException, status


class RateLimiter:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        """Check sliding-window rate limit for a given key.

        Raises HTTP 429 Too Many Requests if limit is exceeded.
        """
        now = time.time()
        clear_before = now - window_seconds
        rate_key = f"rate_limit:{key}"

        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(rate_key, 0, clear_before)
        pipe.zadd(rate_key, {f"{now}:{time.time_ns()}": now})
        pipe.zcard(rate_key)
        pipe.expire(rate_key, window_seconds + 1)
        _, _, count, _ = await pipe.execute()

        if count > max_requests:
            retry_after = int(window_seconds)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s.",
                headers={"Retry-After": str(retry_after)},
            )
