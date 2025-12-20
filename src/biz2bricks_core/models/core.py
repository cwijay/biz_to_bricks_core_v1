"""
Core models: Organizations, Users, Folders.

These are the foundational models for multi-tenant document management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Text, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from biz2bricks_core.models.base import Base

if TYPE_CHECKING:
    from biz2bricks_core.models.documents import DocumentModel, AuditLogModel


class OrganizationModel(Base):
    """
    Organization table for multi-tenancy.

    Stores organization data including plan type and settings.
    """

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255))
    plan_type: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Subscription plan reference (for tiered pricing)
    plan_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("subscription_plans.id"), nullable=True
    )
    subscription_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, past_due, canceled, trialing

    # Relationships
    users: Mapped[List["UserModel"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    folders: Mapped[List["FolderModel"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    documents: Mapped[List["DocumentModel"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_organizations_is_active", "is_active"),
        Index("idx_organizations_created_at", "created_at"),
        Index("idx_organizations_active_created", "is_active", "created_at"),
        Index("idx_organizations_plan_id", "plan_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "plan_type": self.plan_type,
            "settings": self.settings,
            "is_active": self.is_active,
            "plan_id": self.plan_id,
            "subscription_status": self.subscription_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserModel(Base):
    """
    User table for authentication and authorization.

    Scoped to organization for multi-tenancy.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship(back_populates="users")

    __table_args__ = (
        Index("idx_users_organization_id", "organization_id"),
        Index("idx_users_email", "email"),
        Index("idx_users_org_email", "organization_id", "email"),
        Index("idx_users_org_username", "organization_id", "username"),
        Index("idx_users_is_active", "is_active"),
        Index("idx_users_org_is_active", "organization_id", "is_active"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excludes password_hash)."""
        return {
            "id": self.id,
            "org_id": self.organization_id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FolderModel(Base):
    """
    Folder table for hierarchical document organization.

    Supports nested folder structure with path tracking.
    """

    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_folder_id: Mapped[Optional[str]] = mapped_column(String(36))
    path: Mapped[str] = mapped_column(Text, default="/", nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship(back_populates="folders")

    __table_args__ = (
        Index("idx_folders_organization_id", "organization_id"),
        Index("idx_folders_parent_id", "parent_folder_id"),
        Index("idx_folders_org_parent", "organization_id", "parent_folder_id"),
        Index("idx_folders_org_name", "organization_id", "name"),
        Index("idx_folders_path", "path"),
        Index("idx_folders_org_is_active", "organization_id", "is_active"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "org_id": self.organization_id,
            "name": self.name,
            "parent_folder_id": self.parent_folder_id,
            "path": self.path,
            "created_by": self.created_by,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
