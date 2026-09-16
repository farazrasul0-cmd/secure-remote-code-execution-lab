"""003_collaborative_rooms

Revision ID: 003_collaborative_rooms
Revises: 002_autograding
Create Date: 2026-09-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_collaborative_rooms"
down_revision: str | None = "002_autograding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create Rooms Table
    op.create_table(
        "rooms",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("language", sa.String(length=30), nullable=False, server_default="python"),
        sa.Column("current_code", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_members", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rooms_owner_id"), "rooms", ["owner_id"], unique=False)

    # 2. Create Room Members Table
    op.create_table(
        "room_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="editor"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_room_members_room_id"), "room_members", ["room_id"], unique=False)
    op.create_index(op.f("ix_room_members_user_id"), "room_members", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_room_members_user_id"), table_name="room_members")
    op.drop_index(op.f("ix_room_members_room_id"), table_name="room_members")
    op.drop_table("room_members")
    op.drop_index(op.f("ix_rooms_owner_id"), table_name="rooms")
    op.drop_table("rooms")
