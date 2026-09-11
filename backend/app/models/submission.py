"""Submission ORM database model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Submission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Code submission record tracking source code, execution status, and telemetry."""

    __tablename__ = "submissions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(30), default="python", nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    stdin_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="PENDING", index=True, nullable=False
    )
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_memory_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    telemetry: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="submissions")
