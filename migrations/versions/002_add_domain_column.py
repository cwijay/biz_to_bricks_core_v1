"""Add domain column to organizations

Revision ID: 002_add_domain
Revises:
Create Date: 2024-12-20

This is a minimal migration to fix the immediate schema drift issue.
The organizations table is missing the 'domain' column that the SQLAlchemy
model expects.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_add_domain"
down_revision: Union[str, None] = None  # No dependency - this is standalone
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to organizations table."""
    # Add domain column
    op.execute("""
        ALTER TABLE organizations
        ADD COLUMN IF NOT EXISTS domain VARCHAR(255)
    """)

    # Add plan_type column with default
    op.execute("""
        ALTER TABLE organizations
        ADD COLUMN IF NOT EXISTS plan_type VARCHAR(50) DEFAULT 'free'
    """)

    # Add settings column with default
    op.execute("""
        ALTER TABLE organizations
        ADD COLUMN IF NOT EXISTS settings JSONB DEFAULT '{}'::jsonb
    """)

    # Create index on domain (partial - only non-null values)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_organizations_domain
        ON organizations (domain)
        WHERE domain IS NOT NULL
    """)


def downgrade() -> None:
    """Remove the domain column."""
    op.execute("DROP INDEX IF EXISTS idx_organizations_domain")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS domain")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS plan_type")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS settings")
