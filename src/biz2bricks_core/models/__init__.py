"""
SQLAlchemy 2.0 async models for PostgreSQL.

Core tables shared across Biz2Bricks applications:
- Organizations: Multi-tenant organization management
- Users: User management with organization scoping
- Folders: Hierarchical folder structure
- Documents: Document metadata (files stored in GCS)
- AuditLogs: Audit trail for all system events

Usage tracking tables:
- UsageEvents: Individual LLM API call tracking
- UsageDailySummary: Daily rollups for billing
- UsageLimits: Organization limits and credits
- ModelPricing: LLM model pricing lookup
- SubscriptionPlans: Tiered pricing plans
"""

from biz2bricks_core.models.base import Base, AuditAction, AuditEntityType
from biz2bricks_core.models.core import OrganizationModel, UserModel, FolderModel
from biz2bricks_core.models.documents import DocumentModel, AuditLogModel
from biz2bricks_core.models.usage import (
    UsageEventModel,
    UsageDailySummaryModel,
    UsageLimitsModel,
    ModelPricingModel,
    SubscriptionPlanModel,
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
    # Usage tracking models
    "UsageEventModel",
    "UsageDailySummaryModel",
    "UsageLimitsModel",
    "ModelPricingModel",
    "SubscriptionPlanModel",
]
