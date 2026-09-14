"""Shared Redis client dependencies and connection utilities."""

from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.core.config import settings


async def get_redis_client() -> AsyncGenerator[Redis, None]:
    """Dependency for ephemeral asynchronous Redis client."""
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()
