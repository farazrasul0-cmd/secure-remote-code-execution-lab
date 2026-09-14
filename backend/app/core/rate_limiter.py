from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.core.logging import logger
from app.core.metrics import RATE_LIMIT_HITS_TOTAL
from app.core.redis import get_redis_client


class RateLimiter:
    """Sliding Window Log Rate Limiter utilizing Redis Sorted Sets (ZSET)."""

    def __init__(
        self,
        max_requests: int = 15,
        window_seconds: int = 60,
        scope: str = "submissions",
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.scope = scope

    async def __call__(
        self,
        request: Request,
        redis_client: Annotated[Redis, Depends(get_redis_client)],
    ) -> None:
        """Evaluate sliding window request threshold for current client or user."""
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)

        identifier = f"user:{user_id}" if user_id else f"ip:{client_ip}"
        key = f"rce:ratelimit:{self.scope}:{identifier}"

        now = time.time()
        window_start = now - self.window_seconds
        member_id = f"{now}:{uuid.uuid4().hex[:8]}"

        try:
            # Execute sliding window evaluation atomically using Redis pipeline
            pipe = redis_client.pipeline(transaction=True)
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = await pipe.execute()

            current_count = results[1]

            if current_count >= self.max_requests:
                RATE_LIMIT_HITS_TOTAL.labels(endpoint=self.scope).inc()
                logger.warning(
                    "Rate limit exceeded for %s on scope '%s' (%d/%d requests)",
                    identifier,
                    self.scope,
                    current_count,
                    self.max_requests,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: maximum {self.max_requests} requests per {self.window_seconds}s.",
                    headers={"Retry-After": str(self.window_seconds)},
                )

            # Record request within current sliding window
            pipe = redis_client.pipeline(transaction=True)
            pipe.zadd(key, {member_id: now})
            pipe.expire(key, self.window_seconds + 5)
            await pipe.execute()

        except HTTPException:
            raise
        except Exception as exc:
            # High-availability fail-open: logging error without disrupting legitimate traffic if broker degrades
            logger.error("Rate limiter Redis evaluation error (failing open): %s", exc)
            return
