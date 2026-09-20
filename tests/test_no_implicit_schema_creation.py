"""Connecting must not create or modify schema.

The schema is owned by Alembic and applied by the deploy-time migration step.
Previously DatabaseManager ran Base.metadata.create_all on first engine setup,
which meant merely connecting with a newer package version silently mutated the
database -- and, because create_all can only add tables and never alter one,
produced schemas that diverged from the migrations.
"""

from unittest.mock import MagicMock, patch

import pytest

from biz2bricks_core.db import connection as conn_mod
from biz2bricks_core.db.connection import DatabaseManager


@pytest.fixture
def direct_config(monkeypatch):
    cfg = MagicMock()
    cfg.USE_CLOUD_SQL_CONNECTOR = False
    cfg.CLOUD_SQL_INSTANCE = None
    cfg.DATABASE_URL = "postgresql+asyncpg://postgres:pw@localhost:5432/doc_intelligence"
    cfg.get_connection_url.return_value = cfg.DATABASE_URL
    cfg.DB_POOL_SIZE = 5
    cfg.DB_MAX_OVERFLOW = 10
    cfg.DB_POOL_TIMEOUT = 30
    cfg.DB_POOL_RECYCLE = 1800
    cfg.DB_ECHO = False
    monkeypatch.setattr(conn_mod, "db_config", cfg)
    return cfg


async def test_engine_setup_does_not_create_tables(direct_config):
    """Engine setup must not touch the schema."""
    from biz2bricks_core.models import Base

    manager = DatabaseManager()
    manager._engines.clear()
    manager._session_factories.clear()

    with patch.object(Base.metadata, "create_all") as create_all:
        await manager.get_engine_async()

    create_all.assert_not_called()


def test_no_implicit_creation_hook_remains():
    """The old _ensure_tables hook and its latch are gone, not merely bypassed."""
    assert not hasattr(DatabaseManager, "_ensure_tables")
    assert not hasattr(DatabaseManager, "_tables_created")


def test_create_tables_still_available_for_local_use():
    """Explicit create_tables() stays for local development and tests."""
    assert callable(DatabaseManager.create_tables)
