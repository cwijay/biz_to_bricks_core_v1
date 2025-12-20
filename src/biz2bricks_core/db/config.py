"""
Database configuration from environment variables.

Supports both Cloud SQL (production) and direct connection (local development).
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class DatabaseConfig(BaseSettings):
    """
    Database configuration loaded from environment variables.

    Supports:
    - Cloud SQL Python Connector (for production)
    - Direct connection URL (for local development)
    """

    # Cloud SQL settings
    CLOUD_SQL_INSTANCE: Optional[str] = Field(default=None)
    USE_CLOUD_SQL_CONNECTOR: bool = Field(default=False)
    CLOUD_SQL_IP_TYPE: str = Field(default="PUBLIC")  # PUBLIC or PRIVATE

    # Database credentials
    DATABASE_USER: str = Field(default="postgres")
    DATABASE_PASSWORD: str = Field(default="")
    DATABASE_NAME: str = Field(default="doc_intelligence")
    DATABASE_HOST: str = Field(default="localhost")
    DATABASE_PORT: int = Field(default=5432)

    # Direct connection URL (overrides individual settings)
    DATABASE_URL: Optional[str] = Field(default=None)

    # Connection pool settings
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)
    DB_POOL_TIMEOUT: int = Field(default=30)
    DB_POOL_RECYCLE: int = Field(default=1800)  # 30 minutes
    DB_ECHO: bool = Field(default=False)

    # Feature flags
    DATABASE_ENABLED: bool = Field(default=True)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def get_connection_url(self) -> str:
        """Get the database connection URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )


# Global config instance
db_config = DatabaseConfig()


def get_db_config() -> DatabaseConfig:
    """Get database configuration (allows reloading from env)."""
    return DatabaseConfig()
