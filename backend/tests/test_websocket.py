"""WebSocket streaming integration tests."""

import uuid

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.main import app


def test_websocket_requires_valid_jwt_token():
    """Verify that unauthenticated WebSocket connections are rejected with 1008 policy violation."""
    client = TestClient(app)
    fake_id = uuid.uuid4()

    # 1. Connection without token
    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(f"/ws/v1/submissions/{fake_id}"),
    ):
        pass
    assert exc_info.value.code == 1008

    # 2. Connection with invalid token
    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(
            f"/ws/v1/submissions/{fake_id}?token=invalid_junk_token"
        ),
    ):
        pass
    assert exc_info.value.code == 1008


def test_websocket_accepts_valid_jwt_token(monkeypatch):
    """Verify that authenticated WebSocket connections are accepted and stream cleanly."""
    valid_token = create_access_token(subject=str(uuid.uuid4()))
    fake_id = uuid.uuid4()

    class MockPubSub:
        async def subscribe(self, channel):
            pass

        async def get_message(self, **kwargs):
            return None

        async def unsubscribe(self, channel):
            pass

        async def aclose(self):
            pass

    class MockRedisWs:
        def pubsub(self):
            return MockPubSub()

        async def lrange(self, key, start, end):
            return ['{"sequence": 0, "event": "stdout", "data": "Hello WS\\n"}']

        async def aclose(self):
            pass

    monkeypatch.setattr(
        "app.api.v1.endpoints.websocket.Redis.from_url",
        lambda *args, **kwargs: MockRedisWs(),
    )

    client = TestClient(app)
    with client.websocket_connect(
        f"/ws/v1/submissions/{fake_id}?token={valid_token}"
    ) as ws:
        # Client should immediately receive the pre-buffered frame
        received_frame = ws.receive_text()
        assert "Hello WS" in received_frame
        assert "sequence" in received_frame
