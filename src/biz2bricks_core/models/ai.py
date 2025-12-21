"""
AI-specific SQLAlchemy models.

These models support AI document processing, generation caching,
long-term memory, and RAG (Retrieval-Augmented Generation) features.

All models include organization_id for multi-tenancy support.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    BigInteger,
    Integer,
    Boolean,
    Float,
    ForeignKey,
    CheckConstraint,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from biz2bricks_core.models.base import Base


# Organization ID type - UUID as string (36 chars)
ORG_ID_TYPE = String(36)


# =============================================================================
# PROCESSING & GENERATION MODELS
# =============================================================================


class ProcessingJobModel(Base):
    """
    Processing job tracking with result caching.

    Tracks document processing tasks and enables cache lookups.
    Multi-tenancy: Scoped by organization_id.
    """
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        ORG_ID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    complexity: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="processing", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    output_path: Mapped[Optional[str]] = mapped_column(Text)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="chk_processing_jobs_status"
        ),
        Index(
            "idx_jobs_org_cache_lookup",
            "organization_id", "document_hash", "model", "status",
            postgresql_where="status = 'completed'"
        ),
        Index("idx_jobs_org_id", "organization_id"),
        Index("idx_jobs_document_hash", "document_hash"),
        Index("idx_jobs_file_name", "file_name"),
        Index("idx_jobs_started_at", "started_at"),
        Index("idx_jobs_status", "status"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "document_hash": self.document_hash,
            "file_name": self.file_name,
            "model": self.model,
            "complexity": self.complexity,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cached": self.cached,
            "output_path": self.output_path,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
        }


class DocumentGenerationModel(Base):
    """
    Generated content cache (summaries, FAQs, questions).

    Stores generated content and options as JSONB.
    Multi-tenancy: Scoped by organization_id.
    """
    __tablename__ = "document_generations"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        ORG_ID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    document_hash: Mapped[Optional[str]] = mapped_column(String(64))
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[Optional[str]] = mapped_column(Text)
    generation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    options: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    processing_time_ms: Mapped[Optional[float]] = mapped_column(Float)
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "generation_type IN ('summary', 'faqs', 'questions', 'all')",
            name="chk_document_generations_type"
        ),
        Index("idx_generations_org_cache", "organization_id", "document_name", "generation_type", "model"),
        Index("idx_generations_org_id", "organization_id"),
        Index("idx_generations_document_name", "document_name"),
        Index("idx_generations_created_at", "created_at"),
        Index("idx_generations_session", "session_id"),
        Index("idx_generations_content", "content", postgresql_using="gin"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "document_hash": self.document_hash,
            "document_name": self.document_name,
            "source_path": self.source_path,
            "generation_type": self.generation_type,
            "content": self.content,
            "options": self.options,
            "model": self.model,
            "processing_time_ms": self.processing_time_ms,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# LONG-TERM MEMORY MODELS
# =============================================================================


class UserPreferenceModel(Base):
    """
    User preferences for long-term memory.

    Multi-tenancy: Scoped by organization_id.
    """
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    organization_id: Mapped[Optional[str]] = mapped_column(
        ORG_ID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    preferred_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    preferred_summary_length: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    preferred_faq_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    preferred_question_count: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    custom_settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
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

    __table_args__ = (
        Index("idx_user_prefs_org_id", "organization_id"),
        Index("idx_user_prefs_org_user", "organization_id", "user_id"),
        Index("idx_user_prefs_updated", "updated_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "preferred_language": self.preferred_language,
            "preferred_summary_length": self.preferred_summary_length,
            "preferred_faq_count": self.preferred_faq_count,
            "preferred_question_count": self.preferred_question_count,
            "custom_settings": self.custom_settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationSummaryModel(Base):
    """
    Conversation summaries for long-term memory.

    Multi-tenancy: Scoped by organization_id.
    """
    __tablename__ = "conversation_summaries"

    session_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    organization_id: Mapped[Optional[str]] = mapped_column(
        ORG_ID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_topics: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    documents_discussed: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    queries_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "agent_type IN ('document', 'sheets')",
            name="chk_conversation_summaries_agent_type"
        ),
        Index("idx_summaries_org_id", "organization_id"),
        Index("idx_summaries_org_user", "organization_id", "user_id"),
        Index("idx_summaries_user_id", "user_id"),
        Index("idx_summaries_user_agent", "user_id", "agent_type"),
        Index("idx_summaries_created_at", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "agent_type": self.agent_type,
            "summary": self.summary,
            "key_topics": self.key_topics,
            "documents_discussed": self.documents_discussed,
            "queries_count": self.queries_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MemoryEntryModel(Base):
    """
    Generic key-value memory storage.

    Provides flexible namespace-based storage.
    Multi-tenancy: Scoped by organization_id.
    """
    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        ORG_ID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    namespace: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
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

    __table_args__ = (
        UniqueConstraint("organization_id", "namespace", "key", name="uq_memory_org_namespace_key"),
        Index("idx_memory_org_id", "organization_id"),
        Index("idx_memory_org_namespace", "organization_id", "namespace"),
        Index("idx_memory_namespace", "namespace"),
        Index("idx_memory_namespace_key", "namespace", "key"),
        Index("idx_memory_data", "data", postgresql_using="gin"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "namespace": self.namespace,
            "key": self.key,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =============================================================================
# RAG MODULE MODELS
# =============================================================================


class FileSearchStoreModel(Base):
    """
    Gemini File Search store registry.

    Persists store metadata and maps organizations to their Gemini stores.
    Each organization has one store (one-store-per-org architecture).
    Multi-tenancy: One store per organization_id.
    """
    __tablename__ = "file_search_stores"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        ORG_ID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    gemini_store_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    gcp_project: Mapped[Optional[str]] = mapped_column(String(255))
    active_documents_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
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
    folders: Mapped[List["DocumentFolderModel"]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'error')",
            name="chk_file_search_stores_status"
        ),
        Index("idx_file_stores_gemini_id", "gemini_store_id"),
        Index("idx_file_stores_display_name", "display_name"),
        Index("idx_file_stores_status", "status"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "gemini_store_id": self.gemini_store_id,
            "display_name": self.display_name,
            "description": self.description,
            "gcp_project": self.gcp_project,
            "active_documents_count": self.active_documents_count,
            "total_size_bytes": self.total_size_bytes,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DocumentFolderModel(Base):
    """
    Document folder hierarchy within organizations.

    Folders organize documents within a Gemini File Search store.
    Supports nested folder structure via parent_folder_id.
    Multi-tenancy: Scoped by organization_id.
    """
    __tablename__ = "document_folders"

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
    store_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("file_search_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    folder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    parent_folder_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("document_folders.id", ondelete="CASCADE"),
        index=True
    )
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
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
    store: Mapped["FileSearchStoreModel"] = relationship(back_populates="folders")
    parent_folder: Mapped[Optional["DocumentFolderModel"]] = relationship(
        remote_side=[id],
        backref="subfolders"
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "parent_folder_id", "folder_name",
            name="uq_folder_org_parent_name"
        ),
        Index("idx_doc_folders_org_id", "organization_id"),
        Index("idx_doc_folders_store_id", "store_id"),
        Index("idx_doc_folders_parent", "parent_folder_id"),
        Index("idx_doc_folders_name", "folder_name"),
        Index("idx_doc_folders_org_name", "organization_id", "folder_name"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "store_id": self.store_id,
            "folder_name": self.folder_name,
            "description": self.description,
            "parent_folder_id": self.parent_folder_id,
            "document_count": self.document_count,
            "total_size_bytes": self.total_size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
