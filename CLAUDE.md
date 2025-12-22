# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**biz2bricks-core** is a shared Python library for Biz2Bricks applications providing:
- SQLAlchemy 2.0 async models for PostgreSQL
- DatabaseManager for async connections (Cloud SQL + direct)
- Auto table creation on first DB access
- UsageService for storage/token tracking and limit enforcement

This library is consumed by:
- `doc_intelligence_backend_api_v2.0` (storage limits)
- `doc_intelligence_ai_v3.0` (token limits)

## Commands

```bash
uv sync                       # Install dependencies
uv sync --all-extras          # Install with dev dependencies
uv run ruff check .           # Lint
uv run ruff check --fix .     # Auto-fix lint issues
uv run black .                # Format
uv run mypy src               # Type check (strict mode)
uv run pytest                 # Run all tests
uv run pytest -x              # Stop on first failure
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
│   ├── base.py          # SQLAlchemy Base, enums (AuditAction, AuditEntityType)
│   ├── core.py          # OrganizationModel, UserModel, FolderModel
│   ├── documents.py     # DocumentModel, AuditLogModel
│   ├── usage.py         # Usage tracking models
│   └── ai.py            # AI processing models (jobs, generations, memory, RAG)
└── services/
    └── usage_service.py # UsageService singleton
```

### Key Design Patterns

**DatabaseManager** (`db/connection.py`):
- Singleton with per-event-loop resource management (handles ThreadPoolExecutor scenarios)
- Supports Cloud SQL Python Connector (production) and direct URLs (local)
- Auto-creates tables from models on first DB access (`_ensure_tables()`)
- Use `async with db.session() as session:` for database operations
- Use `get_session()` as FastAPI dependency

**UsageService** (`services/usage_service.py`):
- Pre-computed storage tracking in `usage_limits.storage_used_bytes` for O(1) lookups
- Atomic updates with `SELECT FOR UPDATE` to prevent race conditions
- Non-blocking token logging (failures logged but don't propagate)
- Storage tiers: free (100MB), starter (1GB), pro (10GB), business (100GB)

### Database Models

**Core multi-tenant models:**
- `OrganizationModel` - Multi-tenant root with plan/subscription info
- `UserModel` - Scoped to organization
- `FolderModel` - Hierarchical document organization
- `DocumentModel` - Document metadata (files in GCS), includes AI fields: `file_hash`, `parsed_path`, `parsed_at`
- `AuditLogModel` - Compliance audit trail with AI event tracking

**AI processing models** (`models/ai.py`):
- `ProcessingJobModel` - Document processing tasks with caching (status: processing/completed/failed)
- `DocumentGenerationModel` - Generated content cache (summary, faqs, questions)
- `UserPreferenceModel` - User preferences for generation settings
- `ConversationSummaryModel` - Long-term memory for agent conversations
- `MemoryEntryModel` - Generic namespace-based key-value storage
- `FileSearchStoreModel` - Gemini File Search store registry (one store per org)
- `DocumentFolderModel` - Folder hierarchy within RAG stores

**Usage tracking models:**
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
- `CLOUD_SQL_IP_TYPE` - PUBLIC or PRIVATE
- `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`, `DATABASE_HOST`, `DATABASE_PORT`
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`
- `DB_ECHO` - Enable SQL query logging
