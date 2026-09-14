"""Problem and TestCase ORM database models for automated grading."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.submission import Submission


class Problem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Problem entity defining algorithmic challenges, constraints, and metadata."""

    __tablename__ = "problems"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(220), unique=True, index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(
        String(20), default="EASY", nullable=False
    )  # EASY, MEDIUM, HARD
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=128, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    test_cases: Mapped[list[TestCase]] = relationship(
        "TestCase",
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="TestCase.order",
    )
    submissions: Mapped[list[Submission]] = relationship(
        "Submission", back_populates="problem"
    )


class TestCase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """TestCase entity containing input/output oracle vectors, weights, and visibility."""

    __tablename__ = "test_cases"

    problem_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Sample vs Hidden
    weight: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )  # Point weight
    order: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )  # Execution sequence
    explanation: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Human explanation for sample cases

    # Relationship
    problem: Mapped[Problem] = relationship("Problem", back_populates="test_cases")
