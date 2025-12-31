"""
Alembic migration environment for biz2bricks_core.

Supports both sync and async migrations with Cloud SQL Connector.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config, create_async_engine

# Load environment variables
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models to ensure they are registered with Base.metadata
# This is critical for autogenerate to detect all tables
from biz2bricks_core.models import Base
from biz2bricks_core.models.core import OrganizationModel, UserModel, FolderModel
from biz2bricks_core.models.documents import DocumentModel, AuditLogModel
from biz2bricks_core.models.usage import (
    SubscriptionTierModel,
    OrganizationSubscriptionModel,
    TokenUsageRecordModel,
    ResourceUsageRecordModel,
    UsageAggregationModel,
)
from biz2bricks_core.models.ai import (
    ProcessingJobModel,
    DocumentGenerationModel,
    UserPreferenceModel,
    ConversationSummaryModel,
    MemoryEntryModel,
    FileSearchStoreModel,
    DocumentFolderModel,
)
from biz2bricks_core.models.sessions import SessionModel
from biz2bricks_core.models.rag import RAGQueryCacheModel
from biz2bricks_core.models.bulk import BulkJobModel, BulkJobDocumentModel

# Set target metadata for autogenerate support
target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Get database URL from environment variables.

    Supports both direct PostgreSQL URLs and Cloud SQL Connector configuration.
    """
    # Check for direct DATABASE_URL first
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Convert postgres:// to postgresql+asyncpg:// for async support
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return database_url

    # Build URL from individual components
    db_name = os.environ.get("DATABASE_NAME", "doc_intelligence")
    db_user = os.environ.get("DATABASE_USER", "postgres")
    db_password = os.environ.get("DATABASE_PASSWORD", "")
    db_host = os.environ.get("DATABASE_HOST", "localhost")
    db_port = os.environ.get("DATABASE_PORT", "5432")

    return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
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
    Run migrations in 'online' mode with async engine.

    Creates an async Engine and associates a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Uses async engine for PostgreSQL with asyncpg.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
