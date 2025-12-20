"""
UsageService - Shared usage tracking and limit enforcement.

This service is designed to be imported by both:
- doc_intelligence_backend_api_v2.0 (storage limits)
- doc_intelligence_ai_v3.0 (token limits)

Key Features:
- Pre-computed storage tracking (using storage_used_bytes column)
- Atomic updates with row-level locking for race condition prevention
- Non-blocking token logging with async fire-and-forget pattern
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

from biz2bricks_core.db import db
from biz2bricks_core.models import (
    OrganizationModel,
    DocumentModel,
)
from biz2bricks_core.models.usage import (
    UsageLimitsModel,
    UsageEventModel,
    SubscriptionPlanModel,
)

logger = logging.getLogger(__name__)


@dataclass
class StorageLimitResult:
    """Result of storage limit check."""

    allowed: bool
    current_bytes: int
    limit_bytes: Optional[int]  # None = unlimited
    remaining_bytes: Optional[int]
    percentage_used: float
    tier: str


@dataclass
class TokenLimitResult:
    """Result of token limit check."""

    allowed: bool
    tokens_used_this_period: int
    monthly_limit: Optional[int]
    remaining_tokens: Optional[int]
    percentage_used: float


class UsageService:
    """
    Centralized usage tracking and limit enforcement.

    Design decisions:
    1. Storage is PRE-COMPUTED in usage_limits.storage_used_bytes for O(1) lookups
    2. Updates use SELECT FOR UPDATE to prevent race conditions
    3. Token logging is async/non-blocking to not slow down API responses
    """

    # Storage tier limits in bytes
    STORAGE_TIERS = {
        "free": 100 * 1024 * 1024,  # 100MB
        "starter": 1024 * 1024 * 1024,  # 1GB
        "pro": 10 * 1024 * 1024 * 1024,  # 10GB
        "business": 100 * 1024 * 1024 * 1024,  # 100GB
    }

    async def check_storage_limit(
        self, org_id: str, additional_bytes: int = 0
    ) -> StorageLimitResult:
        """
        Check if organization can upload additional_bytes.

        Uses pre-computed storage_used_bytes for O(1) lookup.
        Falls back to SUM(file_size) if usage_limits record doesn't exist.

        Args:
            org_id: Organization ID
            additional_bytes: Size of file being uploaded (0 to just check current usage)

        Returns:
            StorageLimitResult with allowed status and usage details
        """
        async with db.session() as session:
            # Get org with plan info
            org_stmt = (
                select(OrganizationModel, SubscriptionPlanModel)
                .outerjoin(
                    SubscriptionPlanModel,
                    OrganizationModel.plan_id == SubscriptionPlanModel.id,
                )
                .where(OrganizationModel.id == org_id)
            )
            result = await session.execute(org_stmt)
            row = result.first()

            if not row:
                logger.warning(f"Organization not found: {org_id}")
                return StorageLimitResult(
                    allowed=False,
                    current_bytes=0,
                    limit_bytes=0,
                    remaining_bytes=0,
                    percentage_used=100.0,
                    tier="unknown",
                )

            org, plan = row
            tier = org.plan_type or "free"

            # Get limit from plan or use default tier limits
            if plan and plan.max_storage_mb:
                limit_bytes = plan.max_storage_mb * 1024 * 1024
            else:
                limit_bytes = self.STORAGE_TIERS.get(tier, self.STORAGE_TIERS["free"])

            # Get current usage from usage_limits (pre-computed)
            usage_stmt = select(UsageLimitsModel).where(
                UsageLimitsModel.organization_id == org_id
            )
            usage_result = await session.execute(usage_stmt)
            usage = usage_result.scalar_one_or_none()

            if usage and usage.storage_used_bytes is not None:
                current_bytes = usage.storage_used_bytes
            else:
                # Fallback: compute from documents table
                current_bytes = await self._compute_storage_from_documents(
                    session, org_id
                )

            total_after = current_bytes + additional_bytes
            allowed = total_after <= limit_bytes
            remaining = max(0, limit_bytes - current_bytes)
            percentage = (current_bytes / limit_bytes * 100) if limit_bytes > 0 else 0

            return StorageLimitResult(
                allowed=allowed,
                current_bytes=current_bytes,
                limit_bytes=limit_bytes,
                remaining_bytes=remaining,
                percentage_used=round(percentage, 2),
                tier=tier,
            )

    async def update_storage_used(self, org_id: str, delta_bytes: int) -> int:
        """
        Atomically update storage_used_bytes.

        Uses row-level locking (FOR UPDATE) to prevent race conditions
        during concurrent uploads.

        Args:
            org_id: Organization ID
            delta_bytes: Bytes to add (positive) or remove (negative)

        Returns:
            New storage_used_bytes value
        """
        async with db.session() as session:
            # Use FOR UPDATE to lock the row
            stmt = (
                select(UsageLimitsModel)
                .where(UsageLimitsModel.organization_id == org_id)
                .with_for_update()
            )
            result = await session.execute(stmt)
            usage = result.scalar_one_or_none()

            if usage:
                new_value = max(0, (usage.storage_used_bytes or 0) + delta_bytes)
                usage.storage_used_bytes = new_value
            else:
                # Create usage_limits record if it doesn't exist
                new_value = max(0, delta_bytes)
                usage = UsageLimitsModel(
                    id=str(uuid4()),
                    organization_id=org_id,
                    storage_used_bytes=new_value,
                )
                session.add(usage)

            await session.flush()
            logger.debug(
                f"Updated storage for org {org_id}: delta={delta_bytes}, new_value={new_value}"
            )
            return new_value

    async def recalculate_storage(self, org_id: str) -> int:
        """
        Recalculate storage from documents table (for repair/sync).

        This should be used sparingly - primarily for:
        - Initial migration
        - Periodic reconciliation jobs
        - Manual repair

        Args:
            org_id: Organization ID

        Returns:
            Current storage usage in bytes
        """
        async with db.session() as session:
            current = await self._compute_storage_from_documents(session, org_id)

            # Upsert usage_limits
            stmt = (
                insert(UsageLimitsModel)
                .values(
                    id=str(uuid4()),
                    organization_id=org_id,
                    storage_used_bytes=current,
                )
                .on_conflict_do_update(
                    index_elements=["organization_id"],
                    set_={"storage_used_bytes": current},
                )
            )
            await session.execute(stmt)
            logger.info(f"Recalculated storage for org {org_id}: {current} bytes")
            return current

    async def log_token_usage(
        self,
        org_id: str,
        user_id: Optional[str],
        feature: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        input_cost: Decimal = Decimal("0"),
        output_cost: Decimal = Decimal("0"),
        cached_tokens: int = 0,
        request_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Log LLM token usage event.

        Non-blocking - failures are logged but don't propagate.

        Args:
            org_id: Organization ID
            user_id: User ID (optional)
            feature: Feature name (e.g., "document_agent", "sheets_agent")
            model: Model name (e.g., "gemini-2.5-flash", "gpt-4o-mini")
            provider: Provider name (e.g., "google", "openai", "anthropic")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            input_cost: Cost of input tokens in USD
            output_cost: Cost of output tokens in USD
            cached_tokens: Number of cached tokens
            request_id: Unique request ID for deduplication
            extra_data: Additional metadata

        Returns:
            Event ID if successful, None otherwise
        """
        try:
            async with db.session() as session:
                event = UsageEventModel(
                    id=str(uuid4()),
                    organization_id=org_id,
                    user_id=user_id,
                    request_id=request_id,
                    feature=feature,
                    model=model,
                    provider=provider,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                    input_cost=input_cost,
                    output_cost=output_cost,
                    extra_data=extra_data or {},
                )
                session.add(event)
                await session.flush()
                logger.debug(
                    f"Logged token usage: org={org_id}, feature={feature}, "
                    f"tokens={input_tokens}+{output_tokens}"
                )
                return event.id
        except Exception as e:
            # Non-blocking - log and continue
            logger.warning(f"Failed to log token usage: {e}")
            return None

    async def check_token_limit(
        self, org_id: str, estimated_tokens: int = 0
    ) -> TokenLimitResult:
        """
        Check if organization has tokens remaining for this billing period.

        Args:
            org_id: Organization ID
            estimated_tokens: Estimated tokens for the upcoming request

        Returns:
            TokenLimitResult with allowed status and usage details
        """
        async with db.session() as session:
            # Get usage limits with plan
            stmt = (
                select(UsageLimitsModel, SubscriptionPlanModel)
                .join(
                    OrganizationModel,
                    UsageLimitsModel.organization_id == OrganizationModel.id,
                )
                .outerjoin(
                    SubscriptionPlanModel,
                    OrganizationModel.plan_id == SubscriptionPlanModel.id,
                )
                .where(UsageLimitsModel.organization_id == org_id)
            )
            result = await session.execute(stmt)
            row = result.first()

            if not row:
                # No limits configured = unlimited
                return TokenLimitResult(
                    allowed=True,
                    tokens_used_this_period=0,
                    monthly_limit=None,
                    remaining_tokens=None,
                    percentage_used=0.0,
                )

            usage, plan = row
            monthly_limit = usage.monthly_token_limit or (
                plan.monthly_token_limit if plan else None
            )
            tokens_used = usage.credit_used_this_period or 0

            if monthly_limit is None:
                return TokenLimitResult(
                    allowed=True,
                    tokens_used_this_period=tokens_used,
                    monthly_limit=None,
                    remaining_tokens=None,
                    percentage_used=0.0,
                )

            total_after = tokens_used + estimated_tokens
            allowed = total_after <= monthly_limit
            remaining = max(0, monthly_limit - tokens_used)
            percentage = (tokens_used / monthly_limit * 100) if monthly_limit > 0 else 0

            return TokenLimitResult(
                allowed=allowed,
                tokens_used_this_period=tokens_used,
                monthly_limit=monthly_limit,
                remaining_tokens=remaining,
                percentage_used=round(percentage, 2),
            )

    async def update_tokens_used(self, org_id: str, tokens: int) -> int:
        """
        Update credit_used_this_period with token count.

        Args:
            org_id: Organization ID
            tokens: Number of tokens to add

        Returns:
            New token usage count
        """
        async with db.session() as session:
            stmt = (
                select(UsageLimitsModel)
                .where(UsageLimitsModel.organization_id == org_id)
                .with_for_update()
            )
            result = await session.execute(stmt)
            usage = result.scalar_one_or_none()

            if usage:
                new_value = (usage.credit_used_this_period or 0) + tokens
                usage.credit_used_this_period = new_value
            else:
                new_value = tokens
                usage = UsageLimitsModel(
                    id=str(uuid4()),
                    organization_id=org_id,
                    credit_used_this_period=new_value,
                )
                session.add(usage)

            await session.flush()
            return new_value

    async def get_storage_usage_summary(self, org_id: str) -> Dict[str, Any]:
        """
        Get storage usage summary for an organization.

        Returns:
            Dict with current_bytes, limit_bytes, percentage, tier, etc.
        """
        result = await self.check_storage_limit(org_id, 0)
        return {
            "organization_id": org_id,
            "storage_used_bytes": result.current_bytes,
            "storage_used_mb": round(result.current_bytes / (1024 * 1024), 2),
            "storage_limit_bytes": result.limit_bytes,
            "storage_limit_mb": (
                round(result.limit_bytes / (1024 * 1024), 2)
                if result.limit_bytes
                else None
            ),
            "remaining_bytes": result.remaining_bytes,
            "remaining_mb": (
                round(result.remaining_bytes / (1024 * 1024), 2)
                if result.remaining_bytes
                else None
            ),
            "percentage_used": result.percentage_used,
            "tier": result.tier,
        }

    async def _compute_storage_from_documents(self, session, org_id: str) -> int:
        """Compute storage by summing file_size from documents table."""
        stmt = select(func.coalesce(func.sum(DocumentModel.file_size), 0)).where(
            DocumentModel.organization_id == org_id,
            DocumentModel.is_active == True,
        )
        result = await session.execute(stmt)
        return result.scalar() or 0


# Singleton instance
usage_service = UsageService()
