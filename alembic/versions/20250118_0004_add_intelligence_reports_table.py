"""Add intelligence_reports table for business intelligence features

Revision ID: 004
Revises: 003
Create Date: 2025-01-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create intelligence_reports table."""
    op.create_table(
        "intelligence_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("folder_id", sa.String(36), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        # Date range for report filtering
        sa.Column("date_range_start", sa.Date, nullable=True),
        sa.Column("date_range_end", sa.Date, nullable=True),
        # Report options
        sa.Column("options", postgresql.JSONB, nullable=True),
        # Processing metrics
        sa.Column("document_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("extracted_record_count", sa.Integer, server_default="0", nullable=False),
        # Generated content
        sa.Column("summary", postgresql.JSONB, nullable=True),
        sa.Column("insights", postgresql.JSONB, nullable=True),
        sa.Column("charts", postgresql.JSONB, nullable=True),
        # Output file paths (GCS)
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("excel_path", sa.String(500), nullable=True),
        sa.Column("json_path", sa.String(500), nullable=True),
        # Error handling
        sa.Column("error_message", sa.Text, nullable=True),
        # Performance tracking
        sa.Column("processing_time_ms", sa.Integer, nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        # Creator tracking
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Create indexes
    op.create_index("idx_intelligence_reports_org_id", "intelligence_reports", ["organization_id"])
    op.create_index("idx_intelligence_reports_folder_id", "intelligence_reports", ["folder_id"])
    op.create_index("idx_intelligence_reports_status", "intelligence_reports", ["status"])
    op.create_index("idx_intelligence_reports_report_type", "intelligence_reports", ["report_type"])
    op.create_index("idx_intelligence_reports_created_at", "intelligence_reports", ["created_at"])
    op.create_index(
        "idx_intelligence_reports_org_folder",
        "intelligence_reports",
        ["organization_id", "folder_id"],
    )
    op.create_index(
        "idx_intelligence_reports_org_status",
        "intelligence_reports",
        ["organization_id", "status"],
    )
    op.create_index(
        "idx_intelligence_reports_org_type",
        "intelligence_reports",
        ["organization_id", "report_type"],
    )


def downgrade() -> None:
    """Drop intelligence_reports table."""
    # Drop indexes
    op.drop_index("idx_intelligence_reports_org_type", table_name="intelligence_reports")
    op.drop_index("idx_intelligence_reports_org_status", table_name="intelligence_reports")
    op.drop_index("idx_intelligence_reports_org_folder", table_name="intelligence_reports")
    op.drop_index("idx_intelligence_reports_created_at", table_name="intelligence_reports")
    op.drop_index("idx_intelligence_reports_report_type", table_name="intelligence_reports")
    op.drop_index("idx_intelligence_reports_status", table_name="intelligence_reports")
    op.drop_index("idx_intelligence_reports_folder_id", table_name="intelligence_reports")
    op.drop_index("idx_intelligence_reports_org_id", table_name="intelligence_reports")
    op.drop_table("intelligence_reports")
