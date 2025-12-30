"""
SQLAlchemy 2.0 async models for PostgreSQL.

Core tables shared across Biz2Bricks applications:
- Organizations: Multi-tenant organization management
- Users: User management with organization scoping
- Folders: Hierarchical folder structure
- Documents: Document metadata (files stored in GCS)
- AuditLogs: Audit trail for all system events

AI processing tables:
- ProcessingJobs: Document processing job tracking
- DocumentGenerations: Generated content cache (summaries, FAQs, questions)
- UserPreferences: User preferences for long-term memory
- ConversationSummaries: Conversation summaries for memory
- MemoryEntries: Generic key-value memory storage
- FileSearchStores: Gemini File Search store registry
- DocumentFolders: Document folder hierarchy for RAG

Usage tracking tables:
- SubscriptionTiers: Admin-editable tier configuration (Free, Pro, Enterprise)
- OrganizationSubscriptions: Per-org subscription state and usage counters
- TokenUsageRecords: Granular token usage logs for analytics
- ResourceUsageRecords: Non-token resource tracking (LlamaParse, file search)
- UsageAggregations: Pre-computed rollups for dashboards

RAG caching tables:
- RAGQueryCache: Semantic cache for RAG queries using pgvector

Bulk processing tables:
- BulkJobs: Bulk document processing job tracking
- BulkJobDocuments: Per-document status within bulk jobs
"""

from biz2bricks_core.models.base import Base, AuditAction, AuditEntityType
from biz2bricks_core.models.core import OrganizationModel, UserModel, FolderModel
from biz2bricks_core.models.documents import DocumentModel, AuditLogModel
from biz2bricks_core.models.ai import (
    ProcessingJobModel,
    DocumentGenerationModel,
    UserPreferenceModel,
    ConversationSummaryModel,
    MemoryEntryModel,
    FileSearchStoreModel,
    DocumentFolderModel,
)
from biz2bricks_core.models.usage import (
    SubscriptionTierModel,
    OrganizationSubscriptionModel,
    TokenUsageRecordModel,
    ResourceUsageRecordModel,
    UsageAggregationModel,
    # Aliases
    SubscriptionTier,
    OrganizationSubscription,
    TokenUsageRecord,
    ResourceUsageRecord,
    UsageAggregation,
)
from biz2bricks_core.models.rag import (
    RAGQueryCacheModel,
    RAGQueryCache,
    PGVECTOR_AVAILABLE,
)
from biz2bricks_core.models.sessions import SessionModel, Session
from biz2bricks_core.models.bulk import (
    BulkJobModel,
    BulkJobDocumentModel,
    BulkJob,
    BulkJobDocument,
)

__all__ = [
    # Base
    "Base",
    "AuditAction",
    "AuditEntityType",
    # Core models
    "OrganizationModel",
    "UserModel",
    "FolderModel",
    # Document models
    "DocumentModel",
    "AuditLogModel",
    # AI processing models
    "ProcessingJobModel",
    "DocumentGenerationModel",
    "UserPreferenceModel",
    "ConversationSummaryModel",
    "MemoryEntryModel",
    "FileSearchStoreModel",
    "DocumentFolderModel",
    # Usage tracking models
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
    # RAG cache models
    "RAGQueryCacheModel",
    "RAGQueryCache",
    "PGVECTOR_AVAILABLE",
    # Session models
    "SessionModel",
    "Session",
    # Bulk processing models
    "BulkJobModel",
    "BulkJobDocumentModel",
    "BulkJob",
    "BulkJobDocument",
]
