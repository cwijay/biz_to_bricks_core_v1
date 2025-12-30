"""
Bulk processing SQLAlchemy models.

Models for tracking bulk document processing jobs and per-document status.
Supports automated document parsing, indexing, and content generation workflows.

All models include organization_id for multi-tenancy support.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from biz2bricks_core.models.base import Base


# Organization ID type - UUID as string (36 chars)
ORG_ID_TYPE = String(36)


# =============================================================================
# BULK PROCESSING MODELS
# =============================================================================


class BulkJobModel(Base):
    """
    Bulk document processing job tracking.

    Tracks batch processing jobs that parse, index, and generate content
    for multiple documents in a folder.
    Multi-tenancy: Scoped by organization_id.
    """
    __tablename__ = "bulk_jobs"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        ORG_ID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    folder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    total_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_llamaparse_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    options: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    documents: Mapped[List["BulkJobDocumentModel"]] = relationship(
        back_populates="bulk_job",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'partial_failure', 'failed', 'cancelled')",
            name="chk_bulk_jobs_status"
        ),
        Index("idx_bulk_jobs_org_id", "organization_id"),
        Index("idx_bulk_jobs_org_status", "organization_id", "status"),
        Index("idx_bulk_jobs_org_folder", "organization_id", "folder_name"),
        Index("idx_bulk_jobs_status", "status"),
        Index("idx_bulk_jobs_created_at", "created_at"),
        Index("idx_bulk_jobs_source_path", "source_path"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "folder_name": self.folder_name,
            "source_path": self.source_path,
            "total_documents": self.total_documents,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "total_tokens_used": self.total_tokens_used,
            "total_llamaparse_pages": self.total_llamaparse_pages,
            "options": self.options,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BulkJobDocumentModel(Base):
    """
    Per-document status within a bulk processing job.

    Tracks individual document processing through parse -> index -> generate stages.
    Multi-tenancy: Inherited from parent bulk_job.
    """
    __tablename__ = "bulk_job_documents"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    bulk_job_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("bulk_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    parsed_path: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parse_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    index_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    generation_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    total_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    token_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llamaparse_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    bulk_job: Mapped["BulkJobModel"] = relationship(back_populates="documents")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'parsing', 'parsed', 'indexing', 'indexed', "
            "'generating', 'completed', 'failed', 'skipped')",
            name="chk_bulk_job_documents_status"
        ),
        Index("idx_bulk_job_docs_job_id", "bulk_job_id"),
        Index("idx_bulk_job_docs_job_status", "bulk_job_id", "status"),
        Index("idx_bulk_job_docs_status", "status"),
        Index("idx_bulk_job_docs_filename", "original_filename"),
        Index("idx_bulk_job_docs_content_hash", "content_hash"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "bulk_job_id": self.bulk_job_id,
            "original_path": self.original_path,
            "original_filename": self.original_filename,
            "parsed_path": self.parsed_path,
            "status": self.status,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "parse_time_ms": self.parse_time_ms,
            "index_time_ms": self.index_time_ms,
            "generation_time_ms": self.generation_time_ms,
            "total_time_ms": self.total_time_ms,
            "token_usage": self.token_usage,
            "llamaparse_pages": self.llamaparse_pages,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Aliases for convenience
BulkJob = BulkJobModel
BulkJobDocument = BulkJobDocumentModel
