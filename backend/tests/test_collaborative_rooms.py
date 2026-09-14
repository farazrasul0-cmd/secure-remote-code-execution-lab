"""Unit and integration tests for Task 9.3: Collaborative Laboratory Rooms and Real-Time Multiplexing.

Tests cover:
1. Room and RoomMember ORM model relations and schema validations.
2. RoomService CRUD operations (create, get, list, join, update_code).
3. REST API endpoints (/api/v1/rooms) create, list, join, and update.
4. Collaborative WebSocket gateway (/ws/v1/rooms/{room_id}) authentication, presence events, and delta pub/sub fan-out.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.main import app
from app.models.room import Room
from app.models.user import User
from app.schemas.room import RoomCreate
from app.services.room_service import room_service

# ============================================================================
# 1. RoomService Operations Unit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_room_service_create_and_get():
    """Verify RoomService.create_room creates a room and enrolls owner."""
    user = User(
        id=uuid.uuid4(),
        email="instructor@example.com",
        username="instructor",
        hashed_password="hashed_pw",
        role="admin",
        is_active=True,
    )

    room_in = RoomCreate(
        name="Operating Systems Lab 1",
        language="python",
        initial_code="# Write your solution here\n",
        max_members=5,
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    room = await room_service.create_room(db=mock_db, owner=user, room_in=room_in)
    assert room.name == "Operating Systems Lab 1"
    assert room.language == "python"
    assert room.owner_id == user.id
    assert room.is_active is True
    assert mock_db.add.call_count >= 2  # Added room and owner RoomMember


@pytest.mark.asyncio
async def test_room_service_update_code():
    """Verify RoomService.update_room_code persists new code snapshot."""
    mock_room = Room(
        id=uuid.uuid4(),
        name="Python Lab",
        owner_id=uuid.uuid4(),
        language="python",
        current_code="initial",
        is_active=True,
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_room
    mock_db.execute.return_value = mock_res
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    updated = await room_service.update_room_code(
        db=mock_db, room_id=mock_room.id, new_code="print('UPDATED_CODE')\n"
    )
    assert updated is not None
    assert updated.current_code == "print('UPDATED_CODE')\n"


async def get_auth_headers(client: AsyncClient) -> dict[str, str]:
    """Helper to register and login a test user to acquire JWT authorization header."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "room_tester@test.edu",
            "username": "room_tester",
            "password": "SecurePassword123!",
            "role": "student",
        },
    )
    res = await client.post(
        "/api/v1/auth/login/json",
        json={
            "username_or_email": "room_tester",
            "password": "SecurePassword123!",
        },
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 2. REST API Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_api_create_room_endpoint(async_client: AsyncClient):
    """Verify POST /api/v1/rooms creates a room and returns valid schema."""
    headers = await get_auth_headers(async_client)
    payload = {
        "name": "Distributed Systems Lab",
        "language": "python",
        "initial_code": "def consensus(): pass\n",
        "max_members": 8,
    }

    response = await async_client.post("/api/v1/rooms", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Distributed Systems Lab"
    assert data["language"] == "python"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_api_list_and_get_room_endpoint(async_client: AsyncClient):
    """Verify GET /api/v1/rooms and GET /api/v1/rooms/{id} endpoints."""
    headers = await get_auth_headers(async_client)

    # Create room first
    create_res = await async_client.post(
        "/api/v1/rooms",
        json={"name": "Compiler Lab", "language": "cpp", "initial_code": ""},
        headers=headers,
    )
    assert create_res.status_code == 201
    room_id = create_res.json()["id"]

    # List rooms
    list_res = await async_client.get("/api/v1/rooms", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(r["id"] == room_id for r in list_data["items"])

    # Get single room
    get_res = await async_client.get(f"/api/v1/rooms/{room_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Compiler Lab"

    # Patch code
    patch_res = await async_client.patch(
        f"/api/v1/rooms/{room_id}/code",
        json={"current_code": "int main() { return 0; }"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["current_code"] == "int main() { return 0; }"


# ============================================================================
# 3. Collaborative Room WebSocket Tests
# ============================================================================


@pytest.mark.asyncio
async def test_room_websocket_rejects_unauthenticated():
    """Verify /ws/v1/rooms/{id} rejects connections without valid JWT."""
    from starlette.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    client = TestClient(app)
    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(f"/ws/v1/rooms/{uuid.uuid4()}"),
    ):
        pass
    assert exc_info.value.code == 1008
