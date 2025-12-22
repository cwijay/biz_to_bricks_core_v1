# biz2bricks-core

Shared core library for Biz2Bricks applications providing SQLAlchemy models, database connection management, and usage tracking services.

## Features

- **SQLAlchemy 2.0 Async Models** - Multi-tenant models for organizations, users, folders, documents, and audit logs
- **AI Processing Models** - Document processing jobs, generation caching, long-term memory, and RAG support
- **DatabaseManager** - Async PostgreSQL connection manager with Cloud SQL Python Connector support and auto table creation
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
    # Core models
    OrganizationModel,
    UserModel,
    FolderModel,
    DocumentModel,
    AuditLogModel,
    # AI processing models
    ProcessingJobModel,
    DocumentGenerationModel,
    MemoryEntryModel,
    FileSearchStoreModel,
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
│   │   └── connection.py     # DatabaseManager (auto-creates tables)
│   ├── models/
│   │   ├── base.py           # Base class, enums
│   │   ├── core.py           # Organization, User, Folder
│   │   ├── documents.py      # Document, AuditLog
│   │   ├── usage.py          # Usage tracking models
│   │   └── ai.py             # AI processing models
│   └── services/
│       └── usage_service.py  # UsageService
├── tests/
└── pyproject.toml
```

## Database Schema

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              MULTI-TENANT ARCHITECTURE                              │
│                    All tables scoped by organization_id (tenant)                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

                           ┌────────────────────────┐
                           │   subscription_plans   │ (Standalone)
                           ├────────────────────────┤
                           │ id              (PK)   │
                           │ name                   │
                           │ monthly_token_limit    │
                           │ max_storage_mb         │
                           └───────────┬────────────┘
                                       │ 1
                                       │
                                       ▼ N
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                   organizations                                       │
│                              (Multi-Tenant Root Entity)                              │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ id (PK) │ name │ domain │ plan_type │ plan_id (FK) │ subscription_status │ settings │
└──────────────────────────────────────────────────────────────────────────────────────┘
      │
      │ 1:N relationships to all tenant-scoped tables
      │
      ├─────────────────┬─────────────────┬─────────────────┬─────────────────┐
      │                 │                 │                 │                 │
      ▼ N               ▼ N               ▼ N               ▼ 1               ▼ 1
┌───────────┐    ┌───────────┐    ┌───────────┐    ┌──────────────┐   ┌─────────────────┐
│   users   │    │  folders  │    │ documents │    │ usage_limits │   │file_search_stores│
├───────────┤    ├───────────┤    ├───────────┤    ├──────────────┤   ├─────────────────┤
│ id   (PK) │    │ id   (PK) │    │ id   (PK) │    │ id      (PK) │   │ id         (PK) │
│ org_id    │    │ org_id    │    │ org_id    │    │ org_id  (UQ) │   │ org_id     (UQ) │
│ email     │    │ name      │    │ filename  │    │ storage_used │   │ gemini_store_id │
│ role      │    │ parent_id ├──┐ │ file_hash │    │ credit_used  │   └────────┬────────┘
└───────────┘    └───────────┘  │ │ parsed_at │    └──────────────┘            │
                      ▲         │ └───────────┘                                │ 1
                      └─────────┘                                              │
                    (self-reference)                                           ▼ N
                                                                    ┌─────────────────┐
                                                                    │document_folders │
                                                                    ├─────────────────┤
                                                                    │ id         (PK) │
                                                                    │ org_id          │
                                                                    │ store_id   (FK) │
                                                                    │ folder_name     │
                                                                    │ parent_id  ─────┼──┐
                                                                    └─────────────────┘  │
                                                                          ▲              │
                                                                          └──────────────┘
                                                                        (self-reference)

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              AI PROCESSING TABLES                                    │
│                         (All scoped by organization_id)                             │
└─────────────────────────────────────────────────────────────────────────────────────┘

organizations ──1:N──► processing_jobs        (Document processing with caching)
              ──1:N──► document_generations   (Cached summaries, FAQs, questions)
              ──1:N──► user_preferences       (User generation settings)
              ──1:N──► conversation_summaries (Agent long-term memory)
              ──1:N──► memory_entries         (Generic key-value storage)
              ──1:N──► audit_logs ──N:1──► processing_jobs (optional FK)

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              USAGE & BILLING TABLES                                  │
│                         (All scoped by organization_id)                             │
└─────────────────────────────────────────────────────────────────────────────────────┘

organizations ──1:N──► usage_events        (Individual LLM API calls)
              ──1:N──► usage_daily_summary (Aggregated daily rollups)
              ──1:1──► usage_limits        (Limits, credits, storage tracking)

model_pricing (Standalone) ── LLM pricing lookup by provider/model

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  KEY CONSTRAINTS                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

• PK  = Primary Key (UUID string)
• FK  = Foreign Key (CASCADE on delete)
• UQ  = Unique constraint (1:1 relationship)
• All FKs to organizations use ON DELETE CASCADE
• usage_limits.org_id and file_search_stores.org_id are unique (one per org)
```

## Models Overview

### Core Models

| Model | Description |
|-------|-------------|
| `OrganizationModel` | Multi-tenant organization with plan/subscription |
| `UserModel` | Users scoped to organization |
| `FolderModel` | Hierarchical folder structure |
| `DocumentModel` | Document metadata (files in GCS) with AI fields (`file_hash`, `parsed_path`, `parsed_at`) |
| `AuditLogModel` | Audit trail for compliance with AI event tracking |

### AI Processing Models

| Model | Description |
|-------|-------------|
| `ProcessingJobModel` | Document processing tasks with result caching |
| `DocumentGenerationModel` | Generated content cache (summaries, FAQs, questions) |
| `UserPreferenceModel` | User preferences for generation settings |
| `ConversationSummaryModel` | Long-term memory for agent conversations |
| `MemoryEntryModel` | Generic namespace-based key-value storage |
| `FileSearchStoreModel` | Gemini File Search store registry (one per org) |
| `DocumentFolderModel` | Folder hierarchy within RAG stores |

### Usage Models

| Model | Description |
|-------|-------------|
| `SubscriptionPlanModel` | Tiered pricing plans (Free, Starter, Pro, Business) |
| `UsageEventModel` | Individual LLM API call records |
| `UsageDailySummaryModel` | Daily aggregated usage for billing |
| `UsageLimitsModel` | Organization limits and credits |
| `ModelPricingModel` | LLM model pricing lookup |

## License

MIT
