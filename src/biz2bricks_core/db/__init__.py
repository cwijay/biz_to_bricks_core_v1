"""
Database connection management for Biz2Bricks.

Provides:
- DatabaseManager: Async PostgreSQL connection manager (Cloud SQL + direct)
- db: Global singleton instance
- get_session: FastAPI dependency injection helper
"""

from biz2bricks_core.db.connection import DatabaseManager, db, get_session

__all__ = [
    "DatabaseManager",
    "db",
    "get_session",
]
