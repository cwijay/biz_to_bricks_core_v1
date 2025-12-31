"""Add bulk processing tables for batch document processing

Revision ID: 003
Revises: 002
Create Date: 2024-12-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create bulk_jobs and bulk_job_documents tables."""
    # Create bulk_jobs table
    op.create_table(
        "bulk_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("folder_name", sa.String(255), nullable=False),
        sa.Column("source_path", sa.Text, nullable=False),
        sa.Column("total_documents", sa.Integer, server_default="0", nullable=False),
        sa.Column("completed_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("skipped_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("total_tokens_used", sa.Integer, server_default="0", nullable=False),
        sa.Column("total_llamaparse_pages", sa.Integer, server_default="0", nullable=False),
        sa.Column("options", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'partial_failure', 'failed', 'cancelled')",
            name="chk_bulk_jobs_status",
        ),
    )

    # Create bulk_jobs indexes
    op.create_index("idx_bulk_jobs_org_id", "bulk_jobs", ["organization_id"])
    op.create_index("idx_bulk_jobs_org_status", "bulk_jobs", ["organization_id", "status"])
    op.create_index("idx_bulk_jobs_org_folder", "bulk_jobs", ["organization_id", "folder_name"])
    op.create_index("idx_bulk_jobs_status", "bulk_jobs", ["status"])
    op.create_index("idx_bulk_jobs_created_at", "bulk_jobs", ["created_at"])
    op.create_index("idx_bulk_jobs_source_path", "bulk_jobs", ["source_path"])

    # Create bulk_job_documents table
    op.create_table(
        "bulk_job_documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "bulk_job_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("bulk_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_path", sa.Text, nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("parsed_path", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("parse_time_ms", sa.Integer, nullable=True),
        sa.Column("index_time_ms", sa.Integer, nullable=True),
        sa.Column("generation_time_ms", sa.Integer, nullable=True),
        sa.Column("total_time_ms", sa.Integer, nullable=True),
        sa.Column("token_usage", sa.Integer, server_default="0", nullable=False),
        sa.Column("llamaparse_pages", sa.Integer, server_default="0", nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'parsing', 'parsed', 'indexing', 'indexed', "
            "'generating', 'completed', 'failed', 'skipped')",
            name="chk_bulk_job_documents_status",
        ),
    )

    # Create bulk_job_documents indexes
    op.create_index("idx_bulk_job_docs_job_id", "bulk_job_documents", ["bulk_job_id"])
    op.create_index("idx_bulk_job_docs_job_status", "bulk_job_documents", ["bulk_job_id", "status"])
    op.create_index("idx_bulk_job_docs_status", "bulk_job_documents", ["status"])
    op.create_index("idx_bulk_job_docs_filename", "bulk_job_documents", ["original_filename"])
    op.create_index("idx_bulk_job_docs_content_hash", "bulk_job_documents", ["content_hash"])


def downgrade() -> None:
    """Drop bulk_job_documents and bulk_jobs tables."""
    # Drop bulk_job_documents indexes
    op.drop_index("idx_bulk_job_docs_content_hash", table_name="bulk_job_documents")
    op.drop_index("idx_bulk_job_docs_filename", table_name="bulk_job_documents")
    op.drop_index("idx_bulk_job_docs_status", table_name="bulk_job_documents")
    op.drop_index("idx_bulk_job_docs_job_status", table_name="bulk_job_documents")
    op.drop_index("idx_bulk_job_docs_job_id", table_name="bulk_job_documents")
    op.drop_table("bulk_job_documents")

    # Drop bulk_jobs indexes
    op.drop_index("idx_bulk_jobs_source_path", table_name="bulk_jobs")
    op.drop_index("idx_bulk_jobs_created_at", table_name="bulk_jobs")
    op.drop_index("idx_bulk_jobs_status", table_name="bulk_jobs")
    op.drop_index("idx_bulk_jobs_org_folder", table_name="bulk_jobs")
    op.drop_index("idx_bulk_jobs_org_status", table_name="bulk_jobs")
    op.drop_index("idx_bulk_jobs_org_id", table_name="bulk_jobs")
    op.drop_table("bulk_jobs")
