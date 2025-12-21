"""
Document and audit models.
"""

from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Text, BigInteger, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from biz2bricks_core.models.base import Base

if TYPE_CHECKING:
    from biz2bricks_core.models.core import OrganizationModel


class DocumentModel(Base):
    """
    Document table for document metadata.

    Actual files are stored in GCS; this table stores metadata only.
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    folder_id: Mapped[Optional[str]] = mapped_column(String(36))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(36), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    doc_metadata: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # AI Processing columns
    file_hash: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )  # SHA-256 content hash for deduplication
    parsed_path: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Path to parsed .md file in GCS
    parsed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )  # When document was parsed

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship(back_populates="documents")

    __table_args__ = (
        Index("idx_documents_organization_id", "organization_id"),
        Index("idx_documents_folder_id", "folder_id"),
        Index("idx_documents_org_active", "organization_id", "is_active"),
        Index("idx_documents_org_folder", "organization_id", "folder_id"),
        Index("idx_documents_status", "status"),
        Index("idx_documents_created_at", "created_at"),
        Index("idx_documents_storage_path", "storage_path"),
        Index("idx_documents_metadata", "metadata", postgresql_using="gin"),
        Index("idx_documents_filename", "filename"),
        Index("idx_documents_org_filename", "organization_id", "filename"),
        Index("idx_documents_uploaded_by", "uploaded_by"),
        Index("idx_documents_file_hash", "file_hash"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "org_id": self.organization_id,
            "folder_id": self.folder_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "storage_path": self.storage_path,
            "status": self.status,
            "uploaded_by": self.uploaded_by,
            "is_active": self.is_active,
            "metadata": self.doc_metadata,
            "file_hash": self.file_hash,
            "parsed_path": self.parsed_path,
            "parsed_at": self.parsed_at.isoformat() if self.parsed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditLogModel(Base):
    """
    Audit log table for tracking all system events.

    Stores comprehensive audit trail for compliance and debugging.
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    session_id: Mapped[Optional[str]] = mapped_column(String(36))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )

    # AI Processing audit columns
    event_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # AI event type (e.g., "document_parsed", "summary_generated")
    document_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 hash of document being processed
    file_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Filename for display
    job_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True
    )  # Reference to processing job

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship()

    __table_args__ = (
        Index("idx_audit_logs_org_id", "organization_id"),
        Index("idx_audit_logs_entity", "entity_type", "entity_id"),
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_created_at", "created_at"),
        Index(
            "idx_audit_logs_org_type_created",
            "organization_id",
            "entity_type",
            "created_at",
        ),
        Index(
            "idx_audit_logs_org_user_created",
            "organization_id",
            "user_id",
            "created_at",
        ),
        # AI processing indexes
        Index("idx_audit_logs_event_type", "event_type"),
        Index("idx_audit_logs_document_hash", "document_hash"),
        Index("idx_audit_logs_file_name", "file_name"),
        Index("idx_audit_logs_job_id", "job_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "session_id": self.session_id,
            "user_agent": self.user_agent,
            "event_type": self.event_type,
            "document_hash": self.document_hash,
            "file_name": self.file_name,
            "job_id": self.job_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
