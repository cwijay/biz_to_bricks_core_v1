"""
Biz2Bricks Core Library.

Shared components for Biz2Bricks applications:
- SQLAlchemy models (organizations, users, folders, documents, audit_logs)
- AI processing models (processing_jobs, document_generations, memory, RAG)
- Usage tracking models (subscription_tiers, organization_subscriptions, usage records)
- RAG caching models (rag_query_cache with pgvector)
- DatabaseManager for async PostgreSQL connections (Cloud SQL + direct)
- Alembic migrations for schema management
"""

__version__ = "0.1.0"

# Re-export commonly used components
from biz2bricks_core.models import (
    Base,
    OrganizationModel,
    UserModel,
    FolderModel,
    DocumentModel,
    AuditLogModel,
    AuditAction,
    AuditEntityType,
    # AI processing models
    ProcessingJobModel,
    DocumentGenerationModel,
    UserPreferenceModel,
    ConversationSummaryModel,
    MemoryEntryModel,
    FileSearchStoreModel,
    DocumentFolderModel,
    # Usage tracking models
    SubscriptionTierModel,
    OrganizationSubscriptionModel,
    TokenUsageRecordModel,
    ResourceUsageRecordModel,
    UsageAggregationModel,
    SubscriptionTier,
    OrganizationSubscription,
    TokenUsageRecord,
    ResourceUsageRecord,
    UsageAggregation,
    # RAG cache models
    RAGQueryCacheModel,
    RAGQueryCache,
    PGVECTOR_AVAILABLE,
    # Session models
    SessionModel,
    Session,
    # Bulk processing models
    BulkJobModel,
    BulkJobDocumentModel,
    BulkJob,
    BulkJobDocument,
)
from biz2bricks_core.db import DatabaseManager, db, get_session

__all__ = [
    # Version
    "__version__",
    # Core Models
    "Base",
    "OrganizationModel",
    "UserModel",
    "FolderModel",
    "DocumentModel",
    "AuditLogModel",
    "AuditAction",
    "AuditEntityType",
    # AI Processing Models
    "ProcessingJobModel",
    "DocumentGenerationModel",
    "UserPreferenceModel",
    "ConversationSummaryModel",
    "MemoryEntryModel",
    "FileSearchStoreModel",
    "DocumentFolderModel",
    # Usage Tracking Models
    "SubscriptionTierModel",
    "OrganizationSubscriptionModel",
    "TokenUsageRecordModel",
    "ResourceUsageRecordModel",
    "UsageAggregationModel",
    "SubscriptionTier",
    "OrganizationSubscription",
    "TokenUsageRecord",
    "ResourceUsageRecord",
    "UsageAggregation",
    # RAG Cache Models
    "RAGQueryCacheModel",
    "RAGQueryCache",
    "PGVECTOR_AVAILABLE",
    # Session Models
    "SessionModel",
    "Session",
    # Bulk Processing Models
    "BulkJobModel",
    "BulkJobDocumentModel",
    "BulkJob",
    "BulkJobDocument",
    # Database
    "DatabaseManager",
    "db",
    "get_session",
]
