"""REST API endpoints for Collaborative Laboratory Rooms."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.room import (
    RoomCodeUpdate,
    RoomCreate,
    RoomListResponse,
    RoomMemberResponse,
    RoomResponse,
)
from app.services.room_service import room_service

router = APIRouter()


@router.post(
    "",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new collaborative room",
)
async def create_room(
    room_in: RoomCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoomResponse:
    """Create a collaborative coding room with the authenticated user as owner."""
    room = await room_service.create_room(db=db, owner=current_user, room_in=room_in)
    return RoomResponse.model_validate(room)


@router.get(
    "",
    response_model=RoomListResponse,
    summary="List active collaborative rooms",
)
async def list_rooms(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=50, description="Items per page"),
) -> RoomListResponse:
    """List publicly joinable active coding rooms."""
    items, total = await room_service.list_rooms(db=db, page=page, page_size=page_size)
    return RoomListResponse(
        items=[RoomResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{room_id}",
    response_model=RoomResponse,
    summary="Get room details by ID",
)
async def get_room(
    room_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> RoomResponse:
    """Fetch collaborative room configuration and latest code snapshot."""
    room = await room_service.get_room(db=db, room_id=room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collaborative room '{room_id}' not found.",
        )
    return RoomResponse.model_validate(room)


@router.post(
    "/{room_id}/join",
    response_model=RoomMemberResponse,
    summary="Join a collaborative room",
)
async def join_room(
    room_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> RoomMemberResponse:
    """Enroll the current user into an active collaborative room."""
    room = await room_service.get_room(db=db, room_id=room_id)
    if not room or not room.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found or is currently closed.",
        )
    member = await room_service.join_room(db=db, room_id=room_id, user=current_user)
    return RoomMemberResponse.model_validate(member)


@router.patch(
    "/{room_id}/code",
    response_model=RoomResponse,
    summary="Update room code snapshot",
)
async def update_room_code(
    room_id: uuid.UUID,
    code_in: RoomCodeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> RoomResponse:
    """Persist latest code changes into PostgreSQL snapshot."""
    room = await room_service.update_room_code(
        db=db, room_id=room_id, new_code=code_in.current_code
    )
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )
    return RoomResponse.model_validate(room)
