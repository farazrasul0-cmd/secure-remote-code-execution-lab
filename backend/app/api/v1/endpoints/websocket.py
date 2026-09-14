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
    stream_channel = f"rce:stream:{sub_id_str}"
    input_channel = f"rce:input:{sub_id_str}"
    buffer_key = f"rce:buffer:{sub_id_str}"

    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()

    async def downstream_pump():
        """Pipes execution stream chunks from Redis to WebSocket."""
        # 1. Flush any pre-buffered frames (catch-up replay)
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

        # 2. Live stream from Redis Pub/Sub channel
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=0.5
            )
            if message and message.get("type") == "message":
                data_str = message.get("data")
                if data_str:
                    try:
                        frame_data = json.loads(data_str)
                        seq = frame_data.get("sequence", 0)
                        if seq > last_seq:
                            await websocket.send_text(data_str)
                            last_seq = seq

                        if frame_data.get("event") in ["complete", "error"]:
                            await asyncio.sleep(0.1)
                            break
                    except Exception:
                        await websocket.send_text(data_str)

            if websocket.client_state.name != "CONNECTED":
                break
            await asyncio.sleep(0.01)

    async def upstream_pump():
        """Reads user inputs, resize commands, and signals from WebSocket and forwards to Redis."""
        while True:
            try:
                raw_text = await websocket.receive_text()
                if not raw_text:
                    continue

                try:
                    frame = json.loads(raw_text)
                    frame_type = frame.get("type")
                    if frame_type in ["stdin", "resize", "signal"]:
                        await redis_client.publish(input_channel, raw_text)
                except json.JSONDecodeError:
                    # If raw text received, wrap into stdin frame
                    frame = {"type": "stdin", "data": raw_text}
                    await redis_client.publish(input_channel, json.dumps(frame))
            except WebSocketDisconnect:
                break
            except Exception as exc:
                logger.debug("Upstream reader closed for %s: %s", sub_id_str, exc)
                break

    try:
        await pubsub.subscribe(stream_channel)
        # Concurrently execute downstream and upstream pumps
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(downstream_pump()),
                asyncio.create_task(upstream_pump()),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except WebSocketDisconnect:
        logger.info("Client disconnected from submission stream %s", sub_id_str)
    except Exception as exc:
        logger.error("Error in WebSocket streaming session %s: %s", sub_id_str, exc)
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(stream_channel)
            await pubsub.aclose()
            await redis_client.aclose()
        with contextlib.suppress(Exception):
            await websocket.close()
