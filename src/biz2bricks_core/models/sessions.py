"""
Session model for persistent authentication sessions.

Stores user sessions in the database to survive server restarts.
Sessions are scoped to organizations for multi-tenancy.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import String, Boolean, Index
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from biz2bricks_core.models.base import Base


class SessionModel(Base):
    """
    Session table for persistent authentication.

    Stores user session data to survive server restarts.
    Sessions are loaded into memory on startup and persisted
    on create/update/delete operations.
    """

    __tablename__ = "sessions"

    # Primary key - UUID session identifier
    session_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Multi-tenant fields (no FK to allow flexibility)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # User info cached in session (avoids DB lookup on each request)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)

    # Session timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    last_used: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )

    # Refresh token for session renewal
    refresh_token: Mapped[Optional[str]] = mapped_column(
        String(36), unique=True, nullable=True
    )
    refresh_expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Session status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        # Query by user within organization
        Index("idx_sessions_org_user", "organization_id", "user_id"),
        # Query by organization
        Index("idx_sessions_organization_id", "organization_id"),
        # Cleanup expired sessions
        Index("idx_sessions_expires_at", "expires_at"),
        # Lookup by refresh token
        Index("idx_sessions_refresh_token", "refresh_token"),
        # Active sessions query
        Index("idx_sessions_org_is_active", "organization_id", "is_active"),
    )

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    def is_refresh_expired(self) -> bool:
        """Check if refresh token is expired."""
        if not self.refresh_expires_at:
            return True
        return datetime.now(timezone.utc) > self.refresh_expires_at.replace(
            tzinfo=timezone.utc
        )

    def time_until_expiry(self) -> int:
        """Get seconds until session expiry."""
        if self.is_expired():
            return 0
        delta = self.expires_at.replace(tzinfo=timezone.utc) - datetime.now(
            timezone.utc
        )
        return int(delta.total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "session_id": self.session_id,
            "org_id": self.organization_id,
            "user_id": self.user_id,
            "email": self.email,
            "full_name": self.full_name,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "time_until_expiry": self.time_until_expiry(),
        }


# Alias for consistency with other models
Session = SessionModel
