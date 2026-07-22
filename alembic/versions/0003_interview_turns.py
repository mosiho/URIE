"""Add multi-turn interview columns to debrief_sessions + interviewing status."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_interview_turns"
down_revision: Union[str, None] = "0002_force_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add interviewing to debrief_status enum
    op.execute("ALTER TYPE debrief_status ADD VALUE IF NOT EXISTS 'interviewing'")

    op.add_column(
        "debrief_sessions",
        sa.Column("turns", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "debrief_sessions",
        sa.Column("covered_gaps", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "debrief_sessions",
        sa.Column("next_question", sa.Text(), nullable=True),
    )
    op.add_column(
        "debrief_sessions",
        sa.Column("mode", sa.String(32), nullable=False, server_default="oneshot"),
    )


def downgrade() -> None:
    op.drop_column("debrief_sessions", "mode")
    op.drop_column("debrief_sessions", "next_question")
    op.drop_column("debrief_sessions", "covered_gaps")
    op.drop_column("debrief_sessions", "turns")
    # Postgres cannot easily remove enum values; leave 'interviewing' in place.
