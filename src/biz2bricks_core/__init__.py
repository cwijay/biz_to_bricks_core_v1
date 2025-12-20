"""
Biz2Bricks Core Library.

Shared components for Biz2Bricks applications:
- SQLAlchemy models (organizations, users, folders, documents, audit_logs)
- DatabaseManager for async PostgreSQL connections (Cloud SQL + direct)
- Alembic migrations for schema management
- UsageService for usage tracking and limit enforcement
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
)
from biz2bricks_core.models.usage import (
    SubscriptionPlanModel,
    UsageEventModel,
    UsageDailySummaryModel,
    UsageLimitsModel,
    ModelPricingModel,
)
from biz2bricks_core.db import DatabaseManager, db, get_session
from biz2bricks_core.services import (
    UsageService,
    usage_service,
    StorageLimitResult,
    TokenLimitResult,
)

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
    # Usage Models
    "SubscriptionPlanModel",
    "UsageEventModel",
    "UsageDailySummaryModel",
    "UsageLimitsModel",
    "ModelPricingModel",
    # Database
    "DatabaseManager",
    "db",
    "get_session",
    # Services
    "UsageService",
    "usage_service",
    "StorageLimitResult",
    "TokenLimitResult",
]
