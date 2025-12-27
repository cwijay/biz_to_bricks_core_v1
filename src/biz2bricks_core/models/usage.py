"""
SQLAlchemy models for usage tracking and quota management.

Tables:
- subscription_tiers: Admin-editable tier configuration
- organization_subscriptions: Per-org subscription state and usage counters
- token_usage_records: Granular token usage logs for analytics
- resource_usage_records: Non-token resource tracking (LlamaParse, file search)
- usage_aggregations: Pre-computed rollups for dashboards
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    BigInteger,
    Boolean,
    Numeric,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from biz2bricks_core.models.base import Base


class SubscriptionTierModel(Base):
    """
    Admin-editable subscription tier configuration.

    Stores tier limits and pricing for Free, Pro, and Enterprise plans.
    All limits are editable via admin UI without code changes.
    """
    __tablename__ = "subscription_tiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier = Column(String(50), unique=True, nullable=False)  # free, pro, enterprise
    display_name = Column(String(100), nullable=False)
    description = Column(Text)

    # Token limits
    monthly_token_limit = Column(BigInteger, nullable=False, default=50000)

    # Document processing limits
    monthly_llamaparse_pages = Column(Integer, nullable=False, default=50)
    monthly_file_search_queries = Column(Integer, nullable=False, default=100)
    storage_gb_limit = Column(Numeric(10, 2), nullable=False, default=Decimal("1.0"))

    # Rate limits
    requests_per_minute = Column(Integer, default=60)
    requests_per_day = Column(Integer, default=10000)
    max_file_size_mb = Column(Integer, default=50)
    max_concurrent_jobs = Column(Integer, default=5)

    # Feature flags (JSONB for flexibility)
    features = Column(JSONB, default=dict)
    # Example: {"rag_enabled": true, "custom_models": false, "priority_support": true}

    # Pricing (for display, Stripe is source of truth in Phase 2)
    monthly_price_usd = Column(Numeric(10, 2), default=Decimal("0.00"))
    annual_price_usd = Column(Numeric(10, 2), default=Decimal("0.00"))

    # Stripe integration (Phase 2)
    stripe_product_id = Column(String(100))
    stripe_monthly_price_id = Column(String(100))
    stripe_annual_price_id = Column(String(100))

    # Lifecycle
    is_active = Column(Boolean, default=True)  # Soft delete
    sort_order = Column(Integer, default=0)  # Display order
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = relationship("OrganizationSubscriptionModel", back_populates="tier")

    __table_args__ = (
        {'extend_existing': True},
    )

    def __repr__(self):
        return f"<SubscriptionTier(tier='{self.tier}', tokens={self.monthly_token_limit})>"


class OrganizationSubscriptionModel(Base):
    """
    Per-organization subscription state and usage counters.

    Tracks subscription tier, billing period, and current period usage.
    Usage counters are atomically incremented via SQL for thread safety.
    """
    __tablename__ = "organization_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Note: organizations.id is VARCHAR(255), not UUID
    organization_id = Column(String(255), ForeignKey("organizations.id"), unique=True, nullable=False)
    tier_id = Column(UUID(as_uuid=True), ForeignKey("subscription_tiers.id"), nullable=False)

    # Subscription state
    status = Column(String(50), default="active")  # active, past_due, canceled, trialing
    billing_cycle = Column(String(20), default="monthly")  # monthly, annual

    # Billing period (monthly reset)
    current_period_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    current_period_end = Column(DateTime, nullable=False)

    # Usage counters (atomic updates via SQL)
    tokens_used_this_period = Column(BigInteger, default=0)
    llamaparse_pages_used = Column(Integer, default=0)
    file_search_queries_used = Column(Integer, default=0)
    storage_used_bytes = Column(BigInteger, default=0)

    # Denormalized limits (allows custom limits per org, quick access)
    monthly_token_limit = Column(BigInteger, nullable=False)
    monthly_llamaparse_pages_limit = Column(Integer, nullable=False)
    monthly_file_search_queries_limit = Column(Integer, nullable=False)
    storage_limit_bytes = Column(BigInteger, nullable=False)

    # Stripe references (Phase 2)
    stripe_customer_id = Column(String(100), unique=True, index=True)
    stripe_subscription_id = Column(String(100), unique=True, index=True)

    # Trial
    trial_end = Column(DateTime)
    canceled_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tier = relationship("SubscriptionTierModel", back_populates="subscriptions")

    __table_args__ = (
        Index('idx_org_sub_period_end', 'current_period_end'),
        Index('idx_org_sub_status', 'status'),
        {'extend_existing': True},
    )

    def __repr__(self):
        return f"<OrganizationSubscription(org='{self.organization_id}', status='{self.status}')>"

    @property
    def tokens_remaining(self) -> int:
        """Calculate remaining tokens for current period."""
        return max(0, self.monthly_token_limit - self.tokens_used_this_period)

    @property
    def tokens_percentage_used(self) -> float:
        """Calculate percentage of tokens used."""
        if self.monthly_token_limit == 0:
            return 100.0
        return round((self.tokens_used_this_period / self.monthly_token_limit) * 100, 2)

    @property
    def is_quota_exceeded(self) -> bool:
        """Check if any quota is exceeded."""
        return (
            self.tokens_used_this_period >= self.monthly_token_limit or
            self.llamaparse_pages_used >= self.monthly_llamaparse_pages_limit or
            self.file_search_queries_used >= self.monthly_file_search_queries_limit or
            self.storage_used_bytes >= self.storage_limit_bytes
        )


class TokenUsageRecordModel(Base):
    """
    Granular token usage logs for analytics and audit.

    Records actual token counts from LLM responses (not estimates).
    Supports deduplication via request_id for idempotent logging.
    """
    __tablename__ = "token_usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(String(255), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=True)

    # Request identification
    request_id = Column(String(100), unique=True)  # Idempotency key
    session_id = Column(String(100), index=True)

    # Usage details
    feature = Column(String(50), nullable=False, index=True)  # document_agent, sheets_agent, rag_search
    provider = Column(String(50))  # openai, google
    model = Column(String(100))  # gpt-5.1-codex-mini, gemini-3-flash-preview

    # ACTUAL token counts from LLM response
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    cached_tokens = Column(Integer, default=0)

    # Cost tracking
    input_cost_usd = Column(Numeric(12, 8))
    output_cost_usd = Column(Numeric(12, 8))
    total_cost_usd = Column(Numeric(12, 8))

    # Metadata (named extra_metadata to avoid SQLAlchemy reserved name conflict)
    extra_metadata = Column("metadata", JSONB, default=dict)  # document_name, query preview, etc.
    processing_time_ms = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_usage_org_created', 'organization_id', 'created_at'),
        Index('idx_usage_org_feature', 'organization_id', 'feature', 'created_at'),
        {'extend_existing': True},
    )

    def __repr__(self):
        return f"<TokenUsageRecord(feature='{self.feature}', tokens={self.total_tokens})>"


class ResourceUsageRecordModel(Base):
    """
    Non-token resource usage tracking.

    Tracks LlamaParse pages, file search queries, storage changes.
    """
    __tablename__ = "resource_usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(String(255), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=True)

    # Resource type and quantity
    resource_type = Column(String(50), nullable=False)  # llamaparse_pages, file_search_queries, storage_bytes
    amount = Column(Integer, nullable=False)

    # Context
    request_id = Column(String(100))
    file_name = Column(String(500))
    file_path = Column(Text)
    extra_metadata = Column("metadata", JSONB, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_resource_org_type', 'organization_id', 'resource_type', 'created_at'),
        {'extend_existing': True},
    )

    def __repr__(self):
        return f"<ResourceUsageRecord(type='{self.resource_type}', amount={self.amount})>"


class UsageAggregationModel(Base):
    """
    Pre-computed usage aggregations for dashboard performance.

    Daily and monthly rollups for quick reporting without
    scanning all token_usage_records.
    """
    __tablename__ = "usage_aggregations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(String(255), ForeignKey("organizations.id"), nullable=False)

    # Time bucket
    period_type = Column(String(20), nullable=False)  # daily, monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Token aggregates
    total_tokens = Column(BigInteger, default=0)
    total_input_tokens = Column(BigInteger, default=0)
    total_output_tokens = Column(BigInteger, default=0)
    total_cached_tokens = Column(BigInteger, default=0)

    # Feature breakdown
    document_agent_tokens = Column(BigInteger, default=0)
    sheets_agent_tokens = Column(BigInteger, default=0)
    rag_tokens = Column(BigInteger, default=0)

    # Resource aggregates
    llamaparse_pages = Column(Integer, default=0)
    file_search_queries = Column(Integer, default=0)
    storage_delta_bytes = Column(BigInteger, default=0)

    # Cost aggregates
    total_cost_usd = Column(Numeric(12, 4), default=Decimal("0.00"))

    # Request stats
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)

    # Breakdown by feature/model (JSONB for flexibility)
    breakdown_by_feature = Column(JSONB, default=dict)
    breakdown_by_model = Column(JSONB, default=dict)

    aggregated_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('organization_id', 'period_type', 'period_start', name='uq_usage_agg_org_period'),
        Index('idx_usage_agg_org_period', 'organization_id', 'period_type', 'period_start'),
        {'extend_existing': True},
    )

    def __repr__(self):
        return f"<UsageAggregation(org='{self.organization_id}', period='{self.period_type}', tokens={self.total_tokens})>"


# Backwards-compatible aliases
SubscriptionTier = SubscriptionTierModel
OrganizationSubscription = OrganizationSubscriptionModel
TokenUsageRecord = TokenUsageRecordModel
ResourceUsageRecord = ResourceUsageRecordModel
UsageAggregation = UsageAggregationModel

__all__ = [
    "SubscriptionTierModel",
    "OrganizationSubscriptionModel",
    "TokenUsageRecordModel",
    "ResourceUsageRecordModel",
    "UsageAggregationModel",
    # Aliases
    "SubscriptionTier",
    "OrganizationSubscription",
    "TokenUsageRecord",
    "ResourceUsageRecord",
    "UsageAggregation",
]
