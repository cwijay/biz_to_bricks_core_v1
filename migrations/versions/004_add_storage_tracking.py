"""Add storage tracking fields

Revision ID: 004_add_storage_tracking
Revises: 003_clean_slate
Create Date: 2024-12-20

Adds storage limit and tracking fields to support tier-based document processing limits:
- subscription_plans.max_storage_mb: Storage limit per plan tier
- usage_limits.storage_used_bytes: Pre-computed storage usage per org
- usage_limits.storage_limit_bytes: Cached limit from subscription plan

Storage Tier Limits:
- Free: 100 MB
- Starter: 1 GB (1,024 MB)
- Pro: 10 GB (10,240 MB)
- Business: 100 GB (102,400 MB)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004_add_storage_tracking"
down_revision: Union[str, None] = "003_clean_slate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # STEP 1: Add max_storage_mb to subscription_plans
    # ============================================================
    op.execute("""
        ALTER TABLE subscription_plans
        ADD COLUMN max_storage_mb INTEGER
    """)

    # ============================================================
    # STEP 2: Add storage tracking columns to usage_limits
    # ============================================================
    op.execute("""
        ALTER TABLE usage_limits
        ADD COLUMN storage_used_bytes BIGINT NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE usage_limits
        ADD COLUMN storage_limit_bytes BIGINT
    """)

    # Create index for efficient storage queries
    op.execute("""
        CREATE INDEX idx_usage_limits_storage
        ON usage_limits (organization_id, storage_used_bytes)
    """)

    # ============================================================
    # STEP 3: Seed storage limits for existing subscription plans
    # ============================================================
    # Free: 100 MB
    op.execute("""
        UPDATE subscription_plans SET max_storage_mb = 100 WHERE name = 'free'
    """)
    # Starter: 1 GB (1,024 MB)
    op.execute("""
        UPDATE subscription_plans SET max_storage_mb = 1024 WHERE name = 'starter'
    """)
    # Pro: 10 GB (10,240 MB)
    op.execute("""
        UPDATE subscription_plans SET max_storage_mb = 10240 WHERE name = 'pro'
    """)
    # Business: 100 GB (102,400 MB)
    op.execute("""
        UPDATE subscription_plans SET max_storage_mb = 102400 WHERE name = 'business'
    """)


def downgrade() -> None:
    # Remove index first
    op.execute("DROP INDEX IF EXISTS idx_usage_limits_storage")

    # Remove columns from usage_limits
    op.execute("ALTER TABLE usage_limits DROP COLUMN IF EXISTS storage_limit_bytes")
    op.execute("ALTER TABLE usage_limits DROP COLUMN IF EXISTS storage_used_bytes")

    # Remove column from subscription_plans
    op.execute("ALTER TABLE subscription_plans DROP COLUMN IF EXISTS max_storage_mb")
