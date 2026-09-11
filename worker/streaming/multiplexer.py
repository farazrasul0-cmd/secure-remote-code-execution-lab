"""Stream Multiplexer Publishing Container Output to Redis Pub/Sub."""

import json

from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis

from worker.broker.redis_client import redis_broker
from worker.sandbox.models import StreamChunk
from worker.streaming.buffer import StreamBuffer


class StreamMultiplexer:
    """Assigns monotonic sequence numbers to stream chunks and broadcasts via Redis Pub/Sub."""

    def __init__(self, submission_id: str):
        self.submission_id = submission_id
        self.sequence = 0
        self.channel = redis_broker.get_stream_channel(submission_id)

    def _format_payload(self, chunk: StreamChunk) -> str:
        """Format chunk into structured stream frame with monotonic sequence."""
        payload = {
            "submission_id": self.submission_id,
            "sequence": self.sequence,
            "event": chunk.event.value,
            "data": chunk.data,
            "timestamp": chunk.timestamp,
        }
        self.sequence += 1
        return json.dumps(payload)

    async def publish_chunk_async(
        self,
        client: AsyncRedis,
        chunk: StreamChunk,
    ) -> str:
        """Asynchronously publish chunk to Redis Pub/Sub and record in buffer."""
        payload_str = self._format_payload(chunk)
        # 1. Broadcast to active WebSocket listeners
        await client.publish(self.channel, payload_str)
        # 2. Append to short-term catch-up buffer
        await StreamBuffer.append_async(client, self.submission_id, payload_str)
        return payload_str

    def publish_chunk_sync(
        self,
        client: SyncRedis,
        chunk: StreamChunk,
    ) -> str:
        """Synchronously publish chunk to Redis Pub/Sub and record in buffer."""
        payload_str = self._format_payload(chunk)
        # 1. Broadcast to active WebSocket listeners
        client.publish(self.channel, payload_str)
        # 2. Append to short-term catch-up buffer
        StreamBuffer.append_sync(client, self.submission_id, payload_str)
        return payload_str
