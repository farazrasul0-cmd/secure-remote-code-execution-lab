"""002_autograding_problems_and_test_cases

Revision ID: 002_autograding_problems_and_test_cases
Revises: 001_initial_schema
Create Date: 2026-09-14 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_autograding"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create Problems Table
    op.create_table(
        "problems",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "difficulty", sa.String(length=20), nullable=False, server_default="EASY"
        ),
        sa.Column("time_limit_ms", sa.Integer(), nullable=False, server_default="2000"),
        sa.Column(
            "memory_limit_mb", sa.Integer(), nullable=False, server_default="128"
        ),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_problems_slug"), "problems", ["slug"], unique=True)

    # 2. Create Test Cases Table
    op.create_table(
        "test_cases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("problem_id", sa.UUID(), nullable=False),
        sa.Column("input_data", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_test_cases_problem_id"), "test_cases", ["problem_id"], unique=False
    )

    # 3. Add Autograding Columns to Submissions Table
    op.add_column("submissions", sa.Column("problem_id", sa.UUID(), nullable=True))
    op.add_column("submissions", sa.Column("score", sa.Integer(), nullable=True))
    op.add_column("submissions", sa.Column("max_score", sa.Integer(), nullable=True))
    op.add_column(
        "submissions", sa.Column("grading_status", sa.String(length=40), nullable=True)
    )
    op.create_foreign_key(
        "fk_submissions_problem_id",
        "submissions",
        "problems",
        ["problem_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_submissions_problem_id"), "submissions", ["problem_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_submissions_problem_id"), table_name="submissions")
    op.drop_constraint("fk_submissions_problem_id", "submissions", type_="foreignkey")
    op.drop_column("submissions", "grading_status")
    op.drop_column("submissions", "max_score")
    op.drop_column("submissions", "score")
    op.drop_column("submissions", "problem_id")
    op.drop_index(op.f("ix_test_cases_problem_id"), table_name="test_cases")
    op.drop_table("test_cases")
    op.drop_index(op.f("ix_problems_slug"), table_name="problems")
    op.drop_table("problems")
