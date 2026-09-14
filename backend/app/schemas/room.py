"""Pydantic schemas for collaborative laboratory rooms."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
    """Payload for creating a new collaborative room."""

    name: str = Field(
        ..., min_length=3, max_length=120, description="Room display name"
    )
    language: str = Field(default="python", description="Programming language runtime")
    initial_code: str = Field(default="", description="Optional initial source code")
    max_members: int = Field(
        default=10, ge=2, le=50, description="Max concurrent members"
    )


class RoomMemberResponse(BaseModel):
    """Serialized room member metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime = Field(alias="created_at")


class RoomResponse(BaseModel):
    """Serialized collaborative room record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    language: str
    current_code: str
    is_active: bool
    max_members: int
    created_at: datetime
    updated_at: datetime


class RoomListResponse(BaseModel):
    """Paginated list of collaborative rooms."""

    items: list[RoomResponse]
    total: int
    page: int
    page_size: int


class RoomCodeUpdate(BaseModel):
    """Payload for persisting an updated room snapshot."""

    current_code: str = Field(..., description="Full source code snapshot")
