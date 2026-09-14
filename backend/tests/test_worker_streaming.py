"""Unit and integration tests for distributed worker streaming, buffering, and janitor."""

import json
from unittest.mock import MagicMock

import pytest

from worker.janitor.reaper import JanitorReaper
from worker.sandbox.models import (
    ExecutionRequest,
    ExecutionStatus,
    StreamChunk,
    StreamEventType,
)
from worker.streaming.buffer import StreamBuffer
from worker.streaming.multiplexer import StreamMultiplexer
from worker.tasks.execution import _stream_and_collect, execute_code


class MockAsyncRedis:
    """In-memory asynchronous Redis mock for testing streaming and buffer operations."""

    def __init__(self):
        self.published = []
        self.lists = {}
        self.expirations = {}

    async def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1

    async def rpush(self, key: str, value: str) -> int:
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].append(value)
        return len(self.lists[key])

    async def expire(self, key: str, seconds: int) -> bool:
        self.expirations[key] = seconds
        return True

    async def lrange(self, key: str, start: int, end: int):
        items = self.lists.get(key, [])
        if end == -1:
            return items[start:]
        return items[start : end + 1]

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_stream_multiplexer_monotonic_sequence():
    """Verify that StreamMultiplexer increments sequence numbers monotonically."""
    multiplexer = StreamMultiplexer("sub-12345")
    mock_redis = MockAsyncRedis()

    chunk1 = StreamChunk(event=StreamEventType.STDOUT, data="First chunk\n")
    chunk2 = StreamChunk(event=StreamEventType.STDOUT, data="Second chunk\n")

    await multiplexer.publish_chunk_async(mock_redis, chunk1)
    await multiplexer.publish_chunk_async(mock_redis, chunk2)

    assert len(mock_redis.published) == 2
    channel1, msg1 = mock_redis.published[0]
    channel2, msg2 = mock_redis.published[1]

    assert channel1 == "rce:stream:sub-12345"
    assert channel2 == "rce:stream:sub-12345"

    payload1 = json.loads(msg1)
    payload2 = json.loads(msg2)

    assert payload1["sequence"] == 0
    assert payload2["sequence"] == 1
    assert payload1["submission_id"] == "sub-12345"
    assert payload2["submission_id"] == "sub-12345"


@pytest.mark.asyncio
async def test_stream_buffer_ttl_and_replay():
    """Verify that stream chunks are buffered with TTL and can be replayed from offset."""
    mock_redis = MockAsyncRedis()
    submission_id = "sub-replay-test"

    chunks = [
        json.dumps({"sequence": 0, "data": "Line 0"}),
        json.dumps({"sequence": 1, "data": "Line 1"}),
        json.dumps({"sequence": 2, "data": "Line 2"}),
    ]

    for chunk in chunks:
        await StreamBuffer.append_async(mock_redis, submission_id, chunk, ttl=60)

    # Verify TTL set
    buffer_key = f"rce:buffer:{submission_id}"
    assert mock_redis.expirations.get(buffer_key) == 60

    # Verify replay all from start
    replayed_all = await StreamBuffer.get_buffered_async(
        mock_redis, submission_id, start_index=0
    )
    assert len(replayed_all) == 3
    assert replayed_all[0]["sequence"] == 0
    assert replayed_all[2]["sequence"] == 2

    # Verify catch-up replay from offset 1
    replayed_catchup = await StreamBuffer.get_buffered_async(
        mock_redis, submission_id, start_index=1
    )
    assert len(replayed_catchup) == 2
    assert replayed_catchup[0]["sequence"] == 1


def test_janitor_reaper_without_docker():
    """Verify that JanitorReaper safely handles environments where Docker is absent."""
    reaper = JanitorReaper(client=None)
    reaped = reaper.reap_stale_containers()
    assert reaped == []


def test_janitor_reaper_stale_identification():
    """Verify that JanitorReaper identifies containers exceeding max lease."""
    mock_container = MagicMock()
    mock_container.id = "c1234567890"
    mock_container.attrs = {"Created": "2020-01-01T00:00:00.000000Z"}  # Very old

    mock_docker = MagicMock()
    mock_docker.containers.list.return_value = [mock_container]

    reaper = JanitorReaper(max_lease_seconds=30, client=mock_docker)
    reaped = reaper.reap_stale_containers()

    assert len(reaped) == 1
    assert reaped[0] == "c1234567890"
    mock_container.remove.assert_called_once_with(force=True, v=True)


@pytest.mark.asyncio
async def test_stream_and_collect_pipeline(monkeypatch):
    """Verify end-to-end streaming and collection pipeline."""
    mock_redis = MockAsyncRedis()
    monkeypatch.setattr(
        "worker.tasks.execution.redis_broker.get_async_client", lambda: mock_redis
    )

    req = ExecutionRequest(
        source_code="print('Distributed Execution Success')",
        timeout_seconds=2.0,
    )

    result = await _stream_and_collect("sub-test-dist", req, force_process=True)

    assert result["submission_id"] == "sub-test-dist"
    assert result["status"] == ExecutionStatus.COMPLETED.value
    assert "Distributed Execution Success" in result["stdout"]
    assert (
        len(mock_redis.published) >= 2
    )  # Status chunk + stdout chunk + complete chunk


def test_celery_task_registration():
    """Verify that execute_code is a valid callable Celery task."""
    assert callable(execute_code)
    assert execute_code.name == "worker.tasks.execution.execute_code"
