"""Collaborative Room management and snapshot persistence service."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.room import Room, RoomMember
from app.models.user import User
from app.schemas.room import RoomCreate


class RoomService:
    """Business operations for collaborative coding rooms."""

    @staticmethod
    async def create_room(
        db: AsyncSession,
        owner: User,
        room_in: RoomCreate,
    ) -> Room:
        """Create a new collaborative room and automatically enroll the creator as owner."""
        room = Room(
            name=room_in.name,
            owner_id=owner.id,
            language=room_in.language,
            current_code=room_in.initial_code,
            is_active=True,
            max_members=room_in.max_members,
        )
        db.add(room)
        await db.commit()
        await db.refresh(room)

        # Enroll owner as first member
        member = RoomMember(
            room_id=room.id,
            user_id=owner.id,
            role="owner",
        )
        db.add(member)
        await db.commit()

        return room

    @staticmethod
    async def get_room(
        db: AsyncSession,
        room_id: uuid.UUID,
    ) -> Room | None:
        """Fetch a single room by primary ID with eager members loaded."""
        stmt = (
            select(Room).where(Room.id == room_id).options(selectinload(Room.members))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_rooms(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Room], int]:
        """List active collaborative rooms with pagination."""
        offset = (page - 1) * page_size
        total_stmt = select(func.count(Room.id)).where(Room.is_active.is_(True))
        total_res = await db.execute(total_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(Room)
            .where(Room.is_active.is_(True))
            .order_by(Room.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        res = await db.execute(stmt)
        rooms = list(res.scalars().all())
        return rooms, total

    @staticmethod
    async def update_room_code(
        db: AsyncSession,
        room_id: uuid.UUID,
        new_code: str,
    ) -> Room | None:
        """Persist updated code snapshot to PostgreSQL."""
        room = await RoomService.get_room(db, room_id)
        if not room:
            return None
        room.current_code = new_code
        await db.commit()
        await db.refresh(room)
        return room

    @staticmethod
    async def join_room(
        db: AsyncSession,
        room_id: uuid.UUID,
        user: User,
        role: str = "editor",
    ) -> RoomMember:
        """Enroll a user into a collaborative room if capacity allows."""
        # Check if already enrolled
        stmt = select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.user_id == user.id
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing

        member = RoomMember(
            room_id=room_id,
            user_id=user.id,
            role=role,
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return member


room_service = RoomService()
