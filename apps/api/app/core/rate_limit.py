import time
import logging
from typing import Optional
from fastapi import Request
import redis.asyncio as aioredis
from .errors import APIError
from ..config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding-window rate limiter backed by Redis with graceful memory fallback."""

    def __init__(self, times: int = 100, seconds: int = 60, key_prefix: str = "rate_limit"):
        self.times = times
        self.seconds = seconds
        self.key_prefix = key_prefix
        self._memory_fallback: dict = {}

    async def __call__(self, request: Request) -> None:
        # Determine client identifier (authenticated user ID if present, otherwise client host)
        user = getattr(request.state, "user", None)
        client_id = user.id if user else (request.client.host if request.client else "unknown")
        key = f"{self.key_prefix}:{client_id}"
        now = time.time()
        window_start = now - self.seconds

        # Attempt Redis sliding window
        redis_client: Optional[aioredis.Redis] = None
        try:
            redis_client = aioredis.from_url(settings.REDIS_URL, socket_timeout=1.0)
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, self.seconds)
            results = await pipe.execute()
            request_count = results[2]
            await redis_client.aclose()
        except Exception as e:
            # Gracefully fail open or fallback to in-memory sliding window
            if redis_client:
                try:
                    await redis_client.aclose()
                except Exception:
                    pass
            logger.warning(f"Redis rate limiter unavailable ({e}). Using in-memory fallback.")
            
            # In-memory sliding window
            timestamps = self._memory_fallback.setdefault(client_id, [])
            # Prune old timestamps
            self._memory_fallback[client_id] = [t for t in timestamps if t > window_start]
            self._memory_fallback[client_id].append(now)
            request_count = len(self._memory_fallback[client_id])

        if request_count > self.times:
            raise APIError(
                message=f"Too many requests. Limit is {self.times} requests per {self.seconds} seconds.",
                code="RATE_LIMIT_EXCEEDED",
                status_code=429,
                details={"limit": self.times, "window_seconds": self.seconds},
            )
