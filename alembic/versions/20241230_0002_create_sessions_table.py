"""Create sessions table for persistent authentication

Revision ID: 002
Revises: 001
Create Date: 2024-12-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sessions table and indexes."""
    op.create_table(
        "sessions",
        # Primary key
        sa.Column("session_id", sa.String(36), primary_key=True),
        # Multi-tenant fields
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        # User info cached in session
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        # Session timestamps
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_used",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        # Refresh token
        sa.Column("refresh_token", sa.String(36), unique=True, nullable=True),
        sa.Column(
            "refresh_expires_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        # Session status
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
    )

    # Create indexes
    op.create_index(
        "idx_sessions_org_user", "sessions", ["organization_id", "user_id"]
    )
    op.create_index(
        "idx_sessions_organization_id", "sessions", ["organization_id"]
    )
    op.create_index("idx_sessions_expires_at", "sessions", ["expires_at"])
    op.create_index("idx_sessions_refresh_token", "sessions", ["refresh_token"])
    op.create_index(
        "idx_sessions_org_is_active", "sessions", ["organization_id", "is_active"]
    )


def downgrade() -> None:
    """Drop sessions table and indexes."""
    op.drop_index("idx_sessions_org_is_active", table_name="sessions")
    op.drop_index("idx_sessions_refresh_token", table_name="sessions")
    op.drop_index("idx_sessions_expires_at", table_name="sessions")
    op.drop_index("idx_sessions_organization_id", table_name="sessions")
    op.drop_index("idx_sessions_org_user", table_name="sessions")
    op.drop_table("sessions")
