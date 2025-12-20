"""
Usage tracking and subscription models.

Tables for tracking platform usage by tokens and managing tiered subscription plans.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import String, Integer, BigInteger, Boolean, Date, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from biz2bricks_core.models.base import Base


class SubscriptionPlanModel(Base):
    """
    Subscription plan definitions for tiered pricing.

    Plans: Free, Starter ($29), Pro ($99), Business ($299)
    """

    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Pricing (in cents to avoid floating point issues)
    monthly_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    annual_price_cents: Mapped[Optional[int]] = mapped_column(Integer)

    # Limits
    monthly_token_limit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_users: Mapped[Optional[int]] = mapped_column(Integer)  # NULL = unlimited
    max_documents: Mapped[Optional[int]] = mapped_column(Integer)  # NULL = unlimited
    max_storage_mb: Mapped[Optional[int]] = mapped_column(Integer)  # NULL = unlimited

    # Features (JSONB for flexibility)
    features: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_subscription_plans_name", "name"),
        Index("idx_subscription_plans_active", "is_active"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "monthly_price_cents": self.monthly_price_cents,
            "annual_price_cents": self.annual_price_cents,
            "monthly_token_limit": self.monthly_token_limit,
            "max_users": self.max_users,
            "max_documents": self.max_documents,
            "max_storage_mb": self.max_storage_mb,
            "features": self.features,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UsageEventModel(Base):
    """
    Individual LLM API call tracking.

    Records every API call with token counts and costs for billing and analytics.
    """

    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(36))

    # Request details
    request_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    feature: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)

    # Token counts
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Cost (in USD with high precision)
    input_cost: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0)
    output_cost: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0)

    # Extra data (JSONB column named 'metadata' in DB)
    extra_data: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_usage_events_org_created", "organization_id", "created_at"),
        Index("idx_usage_events_org_feature", "organization_id", "feature"),
        Index("idx_usage_events_user", "user_id", "created_at"),
        Index("idx_usage_events_request_id", "request_id"),
    )

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens."""
        return self.input_tokens + self.output_tokens

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost."""
        return self.input_cost + self.output_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "feature": self.feature,
            "model": self.model,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "total_tokens": self.total_tokens,
            "input_cost": float(self.input_cost),
            "output_cost": float(self.output_cost),
            "total_cost": float(self.total_cost),
            "metadata": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UsageDailySummaryModel(Base):
    """
    Daily usage rollups for fast queries and billing.

    Aggregated from usage_events by a scheduled job.
    """

    __tablename__ = "usage_daily_summary"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Aggregated counts
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    total_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)

    # Breakdown by feature
    feature_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Breakdown by model
    model_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_usage_daily_org_date", "organization_id", "date"),
        Index(
            "idx_usage_daily_unique",
            "organization_id",
            "date",
            unique=True,
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "date": self.date.isoformat() if self.date else None,
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": float(self.total_cost),
            "feature_breakdown": self.feature_breakdown,
            "model_breakdown": self.model_breakdown,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UsageLimitsModel(Base):
    """
    Organization usage limits and credits.

    Tracks limits based on subscription plan and credit balance.
    """

    __tablename__ = "usage_limits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Plan-based limits (null = unlimited)
    monthly_token_limit: Mapped[Optional[int]] = mapped_column(BigInteger)
    monthly_request_limit: Mapped[Optional[int]] = mapped_column(Integer)

    # Credit system (prepaid tokens)
    credit_balance: Mapped[int] = mapped_column(BigInteger, default=0)
    credit_used_this_period: Mapped[int] = mapped_column(BigInteger, default=0)

    # Storage tracking (in bytes for precision)
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_limit_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)  # Cached from plan

    # Billing period
    billing_cycle_start: Mapped[Optional[date]] = mapped_column(Date)
    billing_cycle_end: Mapped[Optional[date]] = mapped_column(Date)

    # Alerts
    alert_threshold_percent: Mapped[int] = mapped_column(Integer, default=80)
    alert_sent_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (Index("idx_usage_limits_org", "organization_id"),)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "monthly_token_limit": self.monthly_token_limit,
            "monthly_request_limit": self.monthly_request_limit,
            "credit_balance": self.credit_balance,
            "credit_used_this_period": self.credit_used_this_period,
            "storage_used_bytes": self.storage_used_bytes,
            "storage_limit_bytes": self.storage_limit_bytes,
            "billing_cycle_start": (
                self.billing_cycle_start.isoformat()
                if self.billing_cycle_start
                else None
            ),
            "billing_cycle_end": (
                self.billing_cycle_end.isoformat() if self.billing_cycle_end else None
            ),
            "alert_threshold_percent": self.alert_threshold_percent,
            "alert_sent_at": (
                self.alert_sent_at.isoformat() if self.alert_sent_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ModelPricingModel(Base):
    """
    LLM model pricing lookup table.

    Stores pricing per model/provider for cost calculation.
    """

    __tablename__ = "model_pricing"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    # Price per 1M tokens (in USD)
    input_price_per_million: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False
    )
    output_price_per_million: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False
    )
    cached_price_per_million: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)

    # Validity period
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date)  # NULL = current pricing

    __table_args__ = (
        Index("idx_model_pricing_lookup", "provider", "model", "effective_from"),
        Index(
            "idx_model_pricing_unique",
            "provider",
            "model",
            "effective_from",
            unique=True,
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "provider": self.provider,
            "model": self.model,
            "input_price_per_million": float(self.input_price_per_million),
            "output_price_per_million": float(self.output_price_per_million),
            "cached_price_per_million": float(self.cached_price_per_million),
            "effective_from": (
                self.effective_from.isoformat() if self.effective_from else None
            ),
            "effective_to": (
                self.effective_to.isoformat() if self.effective_to else None
            ),
        }
