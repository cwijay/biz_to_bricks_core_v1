"""
Alembic migration environment.

Supports both sync and async migrations with Cloud SQL connector.
"""

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config, create_async_engine
from dotenv import load_dotenv

from alembic import context

# Load .env from current directory or parent project
env_paths = [
    Path.cwd() / ".env",
    Path.cwd() / ".env.production",
    Path.cwd().parent / "doc_intelligence_backend_api_v2.0" / ".env",
    Path.cwd().parent / "doc_intelligence_backend_api_v2.0" / ".env.production",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

# Import models to register metadata
from biz2bricks_core.models import Base
from biz2bricks_core.db.config import DatabaseConfig

# Reload config after loading env
db_config = DatabaseConfig()

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for 'autogenerate' support
target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from environment or config."""
    # Try environment variable first
    url = os.environ.get("DATABASE_URL")
    if url:
        # Ensure it's async
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Fall back to db_config
    return db_config.get_connection_url()


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async support.

    Creates an async Engine and associates a connection with the context.
    """
    # Check if we should use Cloud SQL Connector
    if db_config.USE_CLOUD_SQL_CONNECTOR and db_config.CLOUD_SQL_INSTANCE:
        connectable = await create_cloud_sql_engine()
    else:
        connectable = create_async_engine(
            get_url(),
            poolclass=pool.NullPool,
        )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


async def create_cloud_sql_engine():
    """Create async engine with Cloud SQL connector."""
    from google.cloud.sql.connector import Connector, IPTypes

    ip_type = (
        IPTypes.PUBLIC
        if db_config.CLOUD_SQL_IP_TYPE == "PUBLIC"
        else IPTypes.PRIVATE
    )

    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)

    async def getconn():
        conn = await connector.connect_async(
            db_config.CLOUD_SQL_INSTANCE,
            "asyncpg",
            user=db_config.DATABASE_USER,
            password=db_config.DATABASE_PASSWORD,
            db=db_config.DATABASE_NAME,
            ip_type=ip_type,
        )
        return conn

    engine = create_async_engine(
        "postgresql+asyncpg://",
        async_creator=getconn,
        poolclass=pool.NullPool,
    )

    return engine


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
