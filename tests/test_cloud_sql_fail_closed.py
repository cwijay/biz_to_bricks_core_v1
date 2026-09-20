"""The Cloud SQL connector must fail closed, never silently use another database.

When USE_CLOUD_SQL_CONNECTOR is set, the operator has named a specific Cloud SQL
instance. Falling back to a direct connection there resolves to DATABASE_URL or
the localhost defaults, so a misconfigured deployment would quietly read and
write the wrong database instead of failing.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from biz2bricks_core.db import connection as conn_mod
from biz2bricks_core.db.connection import CloudSQLConnectionError, DatabaseManager


def _cloud_sql_config():
    cfg = MagicMock()
    cfg.USE_CLOUD_SQL_CONNECTOR = True
    cfg.CLOUD_SQL_INSTANCE = "proj:region:instance"
    cfg.CLOUD_SQL_IP_TYPE = "PUBLIC"
    cfg.DATABASE_USER = "postgres"
    cfg.DATABASE_PASSWORD = "secret"
    cfg.DATABASE_NAME = "doc_intelligence"
    cfg.DATABASE_HOST = "localhost"
    cfg.DATABASE_PORT = 5432
    cfg.DB_POOL_SIZE = 5
    cfg.DB_MAX_OVERFLOW = 10
    cfg.DB_POOL_TIMEOUT = 30
    cfg.DB_POOL_RECYCLE = 1800
    cfg.DB_ECHO = False
    return cfg


@pytest.fixture
def cloud_sql_env(monkeypatch):
    monkeypatch.setattr(conn_mod, "db_config", _cloud_sql_config())


async def test_connector_error_raises_instead_of_falling_back(cloud_sql_env):
    """A connector failure (e.g. 403 from sqladmin) must not reach another database."""
    manager = DatabaseManager()
    connector = MagicMock()

    async def boom(*args, **kwargs):
        raise PermissionError("403 NOT_AUTHORIZED: cloudsql.instances.get")

    connector.connect_async = boom

    with patch("google.cloud.sql.connector.Connector", return_value=connector):
        with patch.object(manager, "_create_direct_engine") as direct:
            with pytest.raises(CloudSQLConnectionError) as exc:
                await manager._create_cloud_sql_engine_async()

    direct.assert_not_called()
    assert "proj:region:instance" in str(exc.value)


async def test_connector_timeout_raises_instead_of_falling_back(cloud_sql_env):
    """A timeout must fail closed too, not silently degrade to localhost."""
    manager = DatabaseManager()
    connector = MagicMock()

    async def hang(*args, **kwargs):
        raise asyncio.TimeoutError()

    connector.connect_async = hang

    with patch("google.cloud.sql.connector.Connector", return_value=connector):
        with patch.object(manager, "_create_direct_engine") as direct:
            with pytest.raises(CloudSQLConnectionError):
                await manager._create_cloud_sql_engine_async()

    direct.assert_not_called()


async def test_missing_connector_package_raises(cloud_sql_env):
    """If the connector package is absent we cannot honour the request; fail closed."""
    manager = DatabaseManager()

    real_import = __import__

    def no_connector(name, *args, **kwargs):
        if name.startswith("google.cloud.sql"):
            raise ImportError("No module named 'google.cloud.sql'")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=no_connector):
        with patch.object(manager, "_create_direct_engine") as direct:
            with pytest.raises(CloudSQLConnectionError):
                await manager._create_cloud_sql_engine_async()

    direct.assert_not_called()


async def test_direct_connection_still_works_when_connector_not_requested(monkeypatch):
    """Local development (USE_CLOUD_SQL_CONNECTOR unset) must be unaffected."""
    cfg = _cloud_sql_config()
    cfg.USE_CLOUD_SQL_CONNECTOR = False
    cfg.CLOUD_SQL_INSTANCE = None
    cfg.DATABASE_URL = "postgresql+asyncpg://postgres:pw@localhost:5432/doc_intelligence"
    cfg.get_connection_url.return_value = cfg.DATABASE_URL
    monkeypatch.setattr(conn_mod, "db_config", cfg)

    engine = DatabaseManager()._create_direct_engine()
    assert engine is not None
