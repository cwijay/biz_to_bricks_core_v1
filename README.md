# biz2bricks-core

Shared core library for Biz2Bricks applications providing SQLAlchemy models, database connection management, and usage tracking services.

## Features

- **SQLAlchemy 2.0 Async Models** - Multi-tenant models for organizations, users, folders, documents, and audit logs
- **DatabaseManager** - Async PostgreSQL connection manager with Cloud SQL Python Connector support
- **Alembic Migrations** - Database schema management with async migration support
- **UsageService** - Storage and token usage tracking with limit enforcement

## Installation

### As a dependency in another project

```bash
# Using uv
uv add biz2bricks-core --extra dev

# Using pip
pip install -e /path/to/biz2bricks_core
```

### For development

```bash
# Clone and install
cd biz2bricks_core
uv sync --all-extras
```

## Configuration

Create a `.env` file with your database settings:

```env
# Direct connection (local development)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/doc_intelligence

# Or individual settings
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=password
DATABASE_NAME=doc_intelligence

# Cloud SQL (production)
USE_CLOUD_SQL_CONNECTOR=true
CLOUD_SQL_INSTANCE=project:region:instance
CLOUD_SQL_IP_TYPE=PUBLIC

# Connection pool
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

## Usage

### Database Sessions

```python
from biz2bricks_core import db, get_session

# Using context manager
async with db.session() as session:
    result = await session.execute(select(OrganizationModel))
    orgs = result.scalars().all()

# As FastAPI dependency
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/orgs")
async def list_orgs(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(OrganizationModel))
    return result.scalars().all()
```

### Models

```python
from biz2bricks_core import (
    OrganizationModel,
    UserModel,
    FolderModel,
    DocumentModel,
    AuditLogModel,
)

# Create an organization
org = OrganizationModel(
    name="Acme Corp",
    domain="acme.com",
    plan_type="starter",
)
session.add(org)
await session.commit()
```

### Usage Tracking

```python
from biz2bricks_core import usage_service, StorageLimitResult

# Check storage limits before upload
result: StorageLimitResult = await usage_service.check_storage_limit(
    org_id="org-uuid",
    additional_bytes=1024 * 1024  # 1MB file
)
if not result.allowed:
    raise HTTPException(413, "Storage limit exceeded")

# Update storage after successful upload
await usage_service.update_storage_used(org_id, file_size)

# Log token usage (non-blocking)
await usage_service.log_token_usage(
    org_id="org-uuid",
    user_id="user-uuid",
    feature="document_agent",
    model="gemini-2.5-flash",
    provider="google",
    input_tokens=1000,
    output_tokens=500,
)
```

## Database Migrations

```bash
# Apply all migrations
uv run alembic upgrade head

# Create a new migration
uv run alembic revision --autogenerate -m "add new column"

# Downgrade one version
uv run alembic downgrade -1

# Show current version
uv run alembic current
```

## Development

### Running Tests

```bash
uv run pytest
uv run pytest -v              # Verbose
uv run pytest -k "test_name"  # Run specific test
```

### Code Quality

```bash
# Linting
uv run ruff check .
uv run ruff check --fix .

# Formatting
uv run black .

# Type checking
uv run mypy src
```

## Project Structure

```
biz2bricks_core/
├── src/biz2bricks_core/
│   ├── __init__.py           # Public API
│   ├── db/
│   │   ├── config.py         # Database configuration
│   │   └── connection.py     # DatabaseManager
│   ├── models/
│   │   ├── base.py           # Base class, enums
│   │   ├── core.py           # Organization, User, Folder
│   │   ├── documents.py      # Document, AuditLog
│   │   └── usage.py          # Usage tracking models
│   └── services/
│       └── usage_service.py  # UsageService
├── migrations/
│   ├── env.py                # Alembic environment
│   └── versions/             # Migration scripts
├── alembic.ini
└── pyproject.toml
```

## Models Overview

### Core Models

| Model | Description |
|-------|-------------|
| `OrganizationModel` | Multi-tenant organization with plan/subscription |
| `UserModel` | Users scoped to organization |
| `FolderModel` | Hierarchical folder structure |
| `DocumentModel` | Document metadata (files stored in GCS) |
| `AuditLogModel` | Audit trail for compliance |

### Usage Models

| Model | Description |
|-------|-------------|
| `SubscriptionPlanModel` | Tiered pricing plans |
| `UsageEventModel` | Individual LLM API call records |
| `UsageDailySummaryModel` | Daily aggregated usage |
| `UsageLimitsModel` | Organization limits and credits |
| `ModelPricingModel` | LLM model pricing lookup |

## License

MIT
