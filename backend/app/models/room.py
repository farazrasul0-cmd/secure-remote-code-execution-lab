"""Collaborative Coding Room ORM models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Room(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Real-time collaborative laboratory room for pair programming and code sync."""

    __tablename__ = "rooms"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(30), default="python", nullable=False)
    current_code: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_members: Mapped[int] = mapped_column(default=10, nullable=False)

    # Relationships
    owner: Mapped[User] = relationship("User")
    members: Mapped[list[RoomMember]] = relationship(
        "RoomMember", back_populates="room", cascade="all, delete-orphan"
    )


class RoomMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Membership record associating users with collaborative rooms."""

    __tablename__ = "room_members"

    room_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), default="editor", nullable=False
    )  # 'owner', 'editor', 'viewer'

    # Relationships
    room: Mapped[Room] = relationship("Room", back_populates="members")
    user: Mapped[User] = relationship("User")
