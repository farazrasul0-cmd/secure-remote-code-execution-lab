"""Unit and integration tests for Task 8.3: Bidirectional Interactive PTY Terminal.

Tests cover:
1. PTYSession lifecycle, window geometry ioctl packing, input writing, signal delivery.
2. Worker upstream input consumer routing stdin, resize, and signal frames to sandbox.
3. Full-duplex WebSocket endpoint accepting upstream user keystrokes, resize, and signals.
4. ProcessSandbox interactive terminal methods (write_stdin, resize_terminal, send_signal).
"""

import asyncio
import json
import signal
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from worker.sandbox.process_sandbox import ProcessSandbox
from worker.sandbox.pty_session import PTYSession
from worker.tasks.execution import _consume_upstream_inputs

# ============================================================================
# 1. PTYSession Tests
# ============================================================================


def test_pty_session_initialization_and_geometry():
    """Verify PTYSession initializes geometry and clamped window dimensions."""
    session = PTYSession(cols=120, rows=40)
    assert session.cols == 120
    assert session.rows == 40
    assert not session.is_open

    # Clamping test: rows < 4 clamped to 4, cols < 10 clamped to 10
    session.set_window_size(cols=5, rows=2)
    assert session.cols == 10
    assert session.rows == 4


def test_pty_session_non_posix_fallback(monkeypatch):
    """Verify PTYSession operates gracefully with standard queue fallback on non-POSIX platforms."""
    monkeypatch.setattr("worker.sandbox.pty_session.IS_POSIX", False)

    session = PTYSession()
    master, slave = session.open()
    assert master is None
    assert slave is None
    assert session.is_open

    # Writing input should enqueue into internal queue
    session.write_input("test command\n")
    assert not session._input_queue.empty()
    assert session._input_queue.get_nowait() == b"test command\n"

    # Resize returns True without error
    assert session.set_window_size(100, 30) is True

    # Signal without PID returns False
    assert session.send_signal(signal.SIGINT) is False

    session.close()
    assert not session.is_open


def test_pty_session_posix_mock(monkeypatch):
    """Verify Linux PTY allocation, termios configuration, and TIOCSWINSZ ioctl call."""
    monkeypatch.setattr("worker.sandbox.pty_session.IS_POSIX", True)

    mock_pty = MagicMock()
    mock_pty.openpty.return_value = (10, 11)

    mock_fcntl = MagicMock()
    mock_fcntl.F_GETFL = 3
    mock_fcntl.F_SETFL = 4
    mock_fcntl.fcntl.return_value = 0

    mock_termios = MagicMock()
    mock_termios.ONLCR = 4
    mock_termios.TCSANOW = 0
    mock_termios.TIOCSWINSZ = 0x5414
    mock_termios.tcgetattr.return_value = [0, 0, 0, 0, 0, 0, []]

    mock_os_write = MagicMock()
    mock_os_close = MagicMock()

    monkeypatch.setattr("worker.sandbox.pty_session.pty", mock_pty)
    monkeypatch.setattr("worker.sandbox.pty_session.fcntl", mock_fcntl)
    monkeypatch.setattr("worker.sandbox.pty_session.termios", mock_termios)
    monkeypatch.setattr("os.write", mock_os_write)
    monkeypatch.setattr("os.close", mock_os_close)

    with PTYSession(cols=80, rows=24) as session:
        assert session.master_fd == 10
        assert session.slave_fd == 11
        assert session.is_open

        # Verify openpty was invoked
        mock_pty.openpty.assert_called_once()
        # Verify non-blocking flag set
        mock_fcntl.fcntl.assert_called()
        # Verify termios ONLCR newline translation set
        mock_termios.tcsetattr.assert_called_once()

        # Test writing input through master_fd
        session.write_input("ls\n")
        mock_os_write.assert_called_with(10, b"ls\n")

        # Test window resize ioctl
        session.set_window_size(120, 35)
        mock_fcntl.ioctl.assert_called()

    # Verify cleanup
    assert not session.is_open
    assert mock_os_close.call_count == 2


def test_pty_session_signal_dispatch(monkeypatch):
    """Verify signal dispatch forwards OS signal to child process."""
    session = PTYSession()
    session.child_pid = 9999

    mock_kill = MagicMock()
    monkeypatch.setattr("os.kill", mock_kill)

    assert session.send_signal(signal.SIGINT) is True
    mock_kill.assert_called_once_with(9999, signal.SIGINT)


# ============================================================================
# 2. Upstream Redis Input Consumer Tests
# ============================================================================


@pytest.mark.asyncio
async def test_consume_upstream_inputs_routing():
    """Verify that _consume_upstream_inputs routes stdin, resize, and signal frames to sandbox."""
    mock_sandbox = MagicMock()
    mock_redis = MagicMock()
    mock_pubsub = MagicMock()

    # Pre-populate messages to simulate incoming websocket frames
    messages = [
        {
            "type": "message",
            "data": json.dumps({"type": "stdin", "data": "hello\n"}),
        },
        {
            "type": "message",
            "data": json.dumps({"type": "resize", "cols": 100, "rows": 30}),
        },
        {
            "type": "message",
            "data": json.dumps({"type": "signal", "signal": "SIGINT"}),
        },
    ]

    async def mock_get_message(**kwargs):
        if messages:
            return messages.pop(0)
        await asyncio.sleep(0.05)
        return None

    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.aclose = AsyncMock()
    mock_pubsub.get_message = mock_get_message
    mock_redis.pubsub.return_value = mock_pubsub

    task = asyncio.create_task(
        _consume_upstream_inputs(mock_sandbox, mock_redis, "rce:input:sub-test-123")
    )

    # Allow loop iterations to process all 3 messages
    await asyncio.sleep(0.1)
    task.cancel()
    await task
    assert task.done()

    mock_sandbox.write_stdin.assert_called_once_with("hello\n")
    mock_sandbox.resize_terminal.assert_called_once_with(100, 30)
    mock_sandbox.send_signal.assert_called_once_with(signal.SIGINT)


# ============================================================================
# 3. Bidirectional WebSocket Upstream Messaging Tests
# ============================================================================


def test_websocket_upstream_input_forwarding(monkeypatch):
    """Verify that user keystrokes sent to WebSocket are published to Redis rce:input channel."""
    valid_token = create_access_token(subject=str(uuid.uuid4()))
    submission_id = uuid.uuid4()
    channel_expected = f"rce:input:{submission_id}"

    published_messages = []

    class MockPubSub:
        async def subscribe(self, channel):
            pass

        async def get_message(self, **kwargs):
            # Stream one stdout frame then complete
            await asyncio.sleep(0.05)
            return {
                "type": "message",
                "data": json.dumps(
                    {"sequence": 0, "event": "stdout", "data": "Python 3.11 REPL\n"}
                ),
            }

        async def unsubscribe(self, channel):
            pass

        async def aclose(self):
            pass

    class MockRedisWs:
        def pubsub(self):
            return MockPubSub()

        async def lrange(self, key, start, end):
            return []

        async def publish(self, channel, message):
            published_messages.append((channel, message))
            return 1

        async def aclose(self):
            pass

    monkeypatch.setattr(
        "app.api.v1.endpoints.websocket.Redis.from_url",
        lambda *args, **kwargs: MockRedisWs(),
    )

    client = TestClient(app)
    with client.websocket_connect(
        f"/ws/v1/submissions/{submission_id}?token={valid_token}"
    ) as ws:
        # Send interactive stdin frame
        ws.send_text(json.dumps({"type": "stdin", "data": "2 + 2\n"}))
        # Send resize frame
        ws.send_text(json.dumps({"type": "resize", "cols": 120, "rows": 30}))
        # Send signal frame
        ws.send_text(json.dumps({"type": "signal", "signal": "SIGINT"}))

        # Receive streamed stdout
        msg = ws.receive_text()
        assert "Python 3.11 REPL" in msg

    # Verify all 3 upstream frames were published to Redis
    assert len(published_messages) >= 3
    channels = [ch for ch, _ in published_messages]
    assert all(ch == channel_expected for ch in channels)

    payloads = [json.loads(body) for _, body in published_messages]
    types = [p["type"] for p in payloads]
    assert "stdin" in types
    assert "resize" in types
    assert "signal" in types


# ============================================================================
# 4. ProcessSandbox Interactive Terminal Methods Tests
# ============================================================================


def test_process_sandbox_interactive_methods():
    """Verify ProcessSandbox forwards stdin, resize, and signal to active process and PTY."""
    sandbox = ProcessSandbox()

    # 1. Without active process or PTY, calls should safely no-op without raising
    sandbox.write_stdin("hello")
    assert sandbox.resize_terminal(80, 24) is False
    assert sandbox.send_signal(signal.SIGINT) is False

    # 2. With active PTY session attached
    mock_pty = MagicMock()
    mock_pty.set_window_size.return_value = True
    mock_pty.send_signal.return_value = True
    sandbox.active_pty = mock_pty

    sandbox.write_stdin("print('hello')\n")
    mock_pty.write_input.assert_called_once_with("print('hello')\n")

    assert sandbox.resize_terminal(100, 32) is True
    mock_pty.set_window_size.assert_called_once_with(100, 32)

    assert sandbox.send_signal(signal.SIGINT) is True
    mock_pty.send_signal.assert_called_once_with(signal.SIGINT)

    # 3. Fallback when active_pty is None but active_process is attached
    sandbox.active_pty = None
    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    sandbox.active_process = mock_proc

    sandbox.write_stdin("test_stdin\n")
    mock_proc.stdin.write.assert_called_once_with(b"test_stdin\n")

    sandbox.send_signal(signal.SIGINT)
    mock_proc.send_signal.assert_called_once_with(signal.SIGINT)
