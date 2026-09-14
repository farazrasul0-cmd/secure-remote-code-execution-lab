"""Stream Buffer Management for Reconnection Resilience and Catch-up."""

import json

from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis

from worker.config import worker_settings


class StreamBuffer:
    """Buffers stream frames in Redis with TTL to guarantee reconnection catch-up."""

    @staticmethod
    async def append_async(
        client: AsyncRedis,
        submission_id: str,
        chunk_json: str,
        ttl: int = worker_settings.BUFFER_TTL_SECONDS,
    ) -> int:
        """Asynchronously append frame to Redis buffer list and set expiration TTL."""
        key = f"{worker_settings.STREAM_BUFFER_PREFIX}{submission_id}"
        length = await client.rpush(key, chunk_json)
        await client.expire(key, ttl)
        return length

    @staticmethod
    def append_sync(
        client: SyncRedis,
        submission_id: str,
        chunk_json: str,
        ttl: int = worker_settings.BUFFER_TTL_SECONDS,
    ) -> int:
        """Synchronously append frame to Redis buffer list and set expiration TTL."""
        key = f"{worker_settings.STREAM_BUFFER_PREFIX}{submission_id}"
        pipe = client.pipeline()
        pipe.rpush(key, chunk_json)
        pipe.expire(key, ttl)
        results = pipe.execute()
        return results[0]

    @staticmethod
    async def get_buffered_async(
        client: AsyncRedis,
        submission_id: str,
        start_index: int = 0,
    ) -> list[dict]:
        """Retrieve missed frames starting from a specified index asynchronously."""
        key = f"{worker_settings.STREAM_BUFFER_PREFIX}{submission_id}"
        raw_items = await client.lrange(key, start_index, -1)
        return [json.loads(item) for item in raw_items]

    @staticmethod
    def get_buffered_sync(
        client: SyncRedis,
        submission_id: str,
        start_index: int = 0,
    ) -> list[dict]:
        """Retrieve missed frames starting from a specified index synchronously."""
        key = f"{worker_settings.STREAM_BUFFER_PREFIX}{submission_id}"
        raw_items = client.lrange(key, start_index, -1)
        return [json.loads(item) for item in raw_items]
