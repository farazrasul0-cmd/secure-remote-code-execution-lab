"""WebSocket endpoint for real-time terminal standard output streaming."""

import asyncio
import contextlib
import json
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import logger
from app.core.security import decode_token

router = APIRouter()


@router.websocket("/submissions/{submission_id}")
async def websocket_stream_submission(
    websocket: WebSocket,
    submission_id: uuid.UUID,
    token: str | None = Query(default=None),
):
    """Full-duplex WebSocket endpoint piping Redis Pub/Sub terminal output to browser."""
    # 1. Authenticate WebSocket handshake
    if not token:
        # Fallback: check headers or reject
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    sub_id_str = str(submission_id)
    channel_name = f"rce:stream:{sub_id_str}"
    buffer_key = f"rce:buffer:{sub_id_str}"

    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()

    try:
        # 2. Subscribe to the submission's Pub/Sub channel
        await pubsub.subscribe(channel_name)

        # 3. Flush any pre-buffered frames (catch-up replay for late connects)
        buffered_frames = await redis_client.lrange(buffer_key, 0, -1)
        last_seq = -1
        for frame_str in buffered_frames:
            try:
                frame_data = json.loads(frame_str)
                seq = frame_data.get("sequence", 0)
                if seq > last_seq:
                    await websocket.send_text(frame_str)
                    last_seq = seq
            except Exception:
                await websocket.send_text(frame_str)

        # 4. Stream live frames from Pub/Sub to WebSocket
        while True:
            # Poll for Redis pub/sub messages with a short timeout
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message.get("type") == "message":
                data_str = message.get("data")
                if data_str:
                    try:
                        frame_data = json.loads(data_str)
                        seq = frame_data.get("sequence", 0)
                        # Avoid duplicates if already flushed from buffer
                        if seq > last_seq:
                            await websocket.send_text(data_str)
                            last_seq = seq

                        # If execution completed, send and exit loop
                        if frame_data.get("event") in ["complete", "error"]:
                            # Allow client brief time to receive final frame
                            await asyncio.sleep(0.1)
                            break
                    except Exception:
                        await websocket.send_text(data_str)

            # Check if WebSocket is still open by checking connection state
            if websocket.client_state.name != "CONNECTED":
                break

            await asyncio.sleep(0.01)

    except WebSocketDisconnect:
        logger.info("Client disconnected from submission stream %s", sub_id_str)
    except Exception as exc:
        logger.error("Error in WebSocket streaming session %s: %s", sub_id_str, exc)
    finally:
        try:
            await pubsub.unsubscribe(channel_name)
            await pubsub.aclose()
            await redis_client.aclose()
        except Exception:
            pass
        with contextlib.suppress(Exception):
            await websocket.close()
