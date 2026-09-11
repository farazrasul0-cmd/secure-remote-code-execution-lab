"""Redis client utilities for queues and pub/sub channels."""

import redis
from redis.asyncio import ConnectionPool as AsyncConnectionPool, Redis as AsyncRedis

from worker.config import worker_settings


class RedisBroker:
    """Manages Redis connection pools and channel keys for queueing and pub/sub."""

    def __init__(self, url: str = worker_settings.REDIS_URL):
        self.url = url
        self._async_pool: AsyncConnectionPool | None = None
        self._sync_client: redis.Redis | None = None

    def get_stream_channel(self, submission_id: str) -> str:
        """Return the pub/sub channel name for streaming a submission's output."""
        return f"{worker_settings.STREAM_CHANNEL_PREFIX}{submission_id}"

    def get_buffer_key(self, submission_id: str) -> str:
        """Return the Redis list key for caching stream chunks."""
        return f"{worker_settings.STREAM_BUFFER_PREFIX}{submission_id}"

    def get_async_client(self) -> AsyncRedis:
        """Obtain an asynchronous Redis client."""
        if not self._async_pool:
            self._async_pool = AsyncConnectionPool.from_url(
                self.url,
                max_connections=50,
                decode_responses=True,
            )
        return AsyncRedis(connection_pool=self._async_pool)

    def get_sync_client(self) -> redis.Redis:
        """Obtain a synchronous Redis client for Celery tasks."""
        if not self._sync_client:
            self._sync_client = redis.Redis.from_url(
                self.url,
                max_connections=20,
                decode_responses=True,
            )
        return self._sync_client

    async def close(self) -> None:
        """Close asynchronous connection pool."""
        if self._async_pool:
            await self._async_pool.disconnect()
            self._async_pool = None


redis_broker = RedisBroker()
