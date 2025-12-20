"""
Base model and common types for SQLAlchemy models.
"""

from enum import Enum as PyEnum

from sqlalchemy.orm import DeclarativeBase


class AuditAction(str, PyEnum):
    """Audit action types for tracking system events."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"
    MOVE = "MOVE"


class AuditEntityType(str, PyEnum):
    """Entity types that can be audited."""

    ORGANIZATION = "ORGANIZATION"
    USER = "USER"
    FOLDER = "FOLDER"
    DOCUMENT = "DOCUMENT"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass
