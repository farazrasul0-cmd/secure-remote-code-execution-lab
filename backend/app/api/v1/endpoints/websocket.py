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


@router.websocket("/rooms/{room_id}")
async def websocket_collaborative_room(
    websocket: WebSocket,
    room_id: uuid.UUID,
    token: str | None = Query(default=None),
):
    """Full-duplex WebSocket endpoint multiplexing real-time code editing, cursor presence, and execution broadcast."""
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id_str = str(payload.get("sub"))
    user_email = payload.get("email", "Anonymous")

    await websocket.accept()
    room_id_str = str(room_id)
    room_sync_channel = f"rce:room:sync:{room_id_str}"
    room_exec_channel = f"rce:room:exec:{room_id_str}"

    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()

    # Announce user presence
    join_event = {
        "type": "presence",
        "action": "joined",
        "user_id": user_id_str,
        "email": user_email,
    }
    await redis_client.publish(room_sync_channel, json.dumps(join_event))

    async def room_downstream_pump():
        """Relays room sync updates (deltas, presence, execution) from Redis to client."""
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=0.5
            )
            if message and message.get("type") == "message":
                data_str = message.get("data")
                if data_str:
                    try:
                        # Forward event frame directly to connected client
                        await websocket.send_text(data_str)
                    except Exception:
                        break

            if websocket.client_state.name != "CONNECTED":
                break
            await asyncio.sleep(0.01)

    async def room_upstream_pump():
        """Receives document changes, cursor shifts, and run commands from client and fans out to Redis."""
        while True:
            try:
                raw_text = await websocket.receive_text()
                if not raw_text:
                    continue

                try:
                    frame = json.loads(raw_text)
                    frame["sender_id"] = user_id_str
                    frame["sender_email"] = user_email

                    frame_type = frame.get("type")
                    if frame_type in ["code_delta", "cursor_move", "chat_message"]:
                        await redis_client.publish(room_sync_channel, json.dumps(frame))
                    elif frame_type == "run_code":
                        # Broadcast run trigger to room execution channel
                        await redis_client.publish(room_exec_channel, json.dumps(frame))
                except json.JSONDecodeError:
                    pass
            except WebSocketDisconnect:
                break
            except Exception as exc:
                logger.debug("Room upstream closed for %s: %s", room_id_str, exc)
                break

    try:
        await pubsub.subscribe(room_sync_channel, room_exec_channel)
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(room_downstream_pump()),
                asyncio.create_task(room_upstream_pump()),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except WebSocketDisconnect:
        logger.info("User %s disconnected from room %s", user_id_str, room_id_str)
    finally:
        # Announce user departure
        leave_event = {
            "type": "presence",
            "action": "left",
            "user_id": user_id_str,
            "email": user_email,
        }
        with contextlib.suppress(Exception):
            await redis_client.publish(room_sync_channel, json.dumps(leave_event))
            await pubsub.unsubscribe(room_sync_channel, room_exec_channel)
            await pubsub.aclose()
            await redis_client.aclose()
        with contextlib.suppress(Exception):
            await websocket.close()
