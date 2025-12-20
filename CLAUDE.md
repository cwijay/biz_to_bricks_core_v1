# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**biz2bricks-core** is a shared Python library for Biz2Bricks applications providing:
- SQLAlchemy 2.0 async models for PostgreSQL
- DatabaseManager for async connections (Cloud SQL + direct)
- Alembic migrations
- UsageService for storage/token tracking and limit enforcement

This library is consumed by:
- `doc_intelligence_backend_api_v2.0` (storage limits)
- `doc_intelligence_ai_v3.0` (token limits)

## Commands

### Setup
```bash
uv sync                    # Install dependencies
uv sync --all-extras       # Install with dev dependencies
```

### Running Migrations
```bash
# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Downgrade
uv run alembic downgrade -1
```

### Linting and Formatting
```bash
uv run ruff check .        # Lint
uv run ruff check --fix .  # Auto-fix
uv run black .             # Format
uv run mypy src            # Type check (strict mode)
```

### Testing
```bash
uv run pytest              # Run all tests
uv run pytest -x           # Stop on first failure
uv run pytest -k "test_name"  # Run specific test
```

## Architecture

### Package Structure
```
src/biz2bricks_core/
├── __init__.py          # Public API exports
├── db/
│   ├── config.py        # DatabaseConfig (pydantic-settings)
│   └── connection.py    # DatabaseManager singleton
├── models/
│   ├── base.py          # SQLAlchemy Base, enums
│   ├── core.py          # OrganizationModel, UserModel, FolderModel
│   ├── documents.py     # DocumentModel, AuditLogModel
│   └── usage.py         # Usage tracking models
└── services/
    └── usage_service.py # UsageService singleton
```

### Key Design Patterns

**DatabaseManager** (`db/connection.py`):
- Singleton with per-event-loop resource management
- Supports Cloud SQL Python Connector (production) and direct URLs (local)
- Use `async with db.session() as session:` for database operations
- Use `get_session()` as FastAPI dependency

**UsageService** (`services/usage_service.py`):
- Pre-computed storage tracking in `usage_limits.storage_used_bytes` for O(1) lookups
- Atomic updates with `SELECT FOR UPDATE` to prevent race conditions
- Non-blocking token logging (failures logged but don't propagate)

### Database Models

Core multi-tenant models:
- `OrganizationModel` - Multi-tenant root with plan/subscription info
- `UserModel` - Scoped to organization
- `FolderModel` - Hierarchical document organization
- `DocumentModel` - Document metadata (files in GCS)
- `AuditLogModel` - Compliance audit trail

Usage tracking models:
- `SubscriptionPlanModel` - Tiered plans (Free, Starter, Pro, Business)
- `UsageEventModel` - Individual LLM API calls
- `UsageDailySummaryModel` - Daily rollups for billing
- `UsageLimitsModel` - Organization limits and credits
- `ModelPricingModel` - LLM model pricing lookup

### Configuration

Environment variables (loaded via pydantic-settings from `.env`):
- `DATABASE_URL` - Direct connection string (overrides individual settings)
- `USE_CLOUD_SQL_CONNECTOR` - Enable Cloud SQL Python Connector
- `CLOUD_SQL_INSTANCE` - Cloud SQL instance connection name
- `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`, `DATABASE_HOST`, `DATABASE_PORT`
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`
