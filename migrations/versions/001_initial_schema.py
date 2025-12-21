"""Initial schema - baseline all tables

Revision ID: 001_initial
Revises:
Create Date: 2024-12-20

Creates the baseline schema for biz2bricks:
- Core tables: organizations, users, folders, documents, audit_logs
- Usage tables: subscription_plans, usage_events, usage_daily_summary, usage_limits, model_pricing

Uses IF NOT EXISTS patterns for safe application to existing databases.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: Using raw SQL with IF NOT EXISTS for safe application to existing DBs

    # === SUBSCRIPTION PLANS (must come first due to FK) ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            display_name VARCHAR(100) NOT NULL,
            monthly_price_cents INTEGER NOT NULL,
            annual_price_cents INTEGER,
            monthly_token_limit BIGINT NOT NULL,
            max_users INTEGER,
            max_documents INTEGER,
            features JSONB NOT NULL DEFAULT '{}',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscription_plans_name
        ON subscription_plans (name)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscription_plans_active
        ON subscription_plans (is_active)
    """)

    # Seed default plans
    op.execute("""
        INSERT INTO subscription_plans (id, name, display_name, monthly_price_cents, monthly_token_limit, max_users, features)
        VALUES
            (gen_random_uuid()::text, 'free', 'Free', 0, 10000, 1, '{"api_access": false}'),
            (gen_random_uuid()::text, 'starter', 'Starter', 2900, 100000, 3, '{"api_access": false}'),
            (gen_random_uuid()::text, 'pro', 'Pro', 9900, 500000, 10, '{"api_access": true, "priority_support": true}'),
            (gen_random_uuid()::text, 'business', 'Business', 29900, 2000000, NULL, '{"api_access": true, "priority_support": true, "custom_branding": true}')
        ON CONFLICT (name) DO NOTHING
    """)

    # === ORGANIZATIONS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            domain VARCHAR(255),
            plan_type VARCHAR(50) NOT NULL DEFAULT 'free',
            settings JSONB NOT NULL DEFAULT '{}',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            plan_id VARCHAR(36) REFERENCES subscription_plans(id),
            subscription_status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)

    # Add missing columns to existing organizations table
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS domain VARCHAR(255)")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan_type VARCHAR(50) DEFAULT 'free'")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS settings JSONB DEFAULT '{}'")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan_id VARCHAR(36)")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) DEFAULT 'active'")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")

    # Add FK constraint if not exists (safe to run even if constraint exists)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'organizations_plan_id_fkey'
                AND table_name = 'organizations'
            ) THEN
                ALTER TABLE organizations
                ADD CONSTRAINT organizations_plan_id_fkey
                FOREIGN KEY (plan_id) REFERENCES subscription_plans(id);
            END IF;
        END $$;
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_organizations_is_active
        ON organizations (is_active)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_organizations_created_at
        ON organizations (created_at)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_organizations_active_created
        ON organizations (is_active, created_at)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_organizations_plan_id
        ON organizations (plan_id)
    """)

    # === USERS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(36) PRIMARY KEY,
            organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL UNIQUE,
            username VARCHAR(100) NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'user',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            last_login TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)

    # Add missing columns to existing users table
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(100)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")

    op.execute("CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_org_email ON users (organization_id, email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_org_username ON users (organization_id, username)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_org_is_active ON users (organization_id, is_active)")

    # === FOLDERS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id VARCHAR(36) PRIMARY KEY,
            organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            parent_folder_id VARCHAR(36),
            path TEXT NOT NULL DEFAULT '/',
            created_by VARCHAR(36) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)

    # Add missing columns to existing folders table
    op.execute("ALTER TABLE folders ADD COLUMN IF NOT EXISTS parent_folder_id VARCHAR(36)")
    op.execute("ALTER TABLE folders ADD COLUMN IF NOT EXISTS path TEXT DEFAULT '/'")
    op.execute("ALTER TABLE folders ADD COLUMN IF NOT EXISTS created_by VARCHAR(36)")
    op.execute("ALTER TABLE folders ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE folders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")

    op.execute("CREATE INDEX IF NOT EXISTS idx_folders_organization_id ON folders (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_folders_parent_id ON folders (parent_folder_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_folders_org_parent ON folders (organization_id, parent_folder_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_folders_org_name ON folders (organization_id, name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_folders_path ON folders (path)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_folders_org_is_active ON folders (organization_id, is_active)")

    # === DOCUMENTS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id VARCHAR(36) PRIMARY KEY,
            organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            folder_id VARCHAR(36),
            filename VARCHAR(255) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            file_type VARCHAR(20) NOT NULL,
            file_size BIGINT NOT NULL,
            storage_path TEXT NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
            uploaded_by VARCHAR(36) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)

    # Add missing columns to existing documents table
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS folder_id VARCHAR(36)")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255)")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_path TEXT")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'uploaded'")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")

    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_organization_id ON documents (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_folder_id ON documents (folder_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_org_active ON documents (organization_id, is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_org_folder ON documents (organization_id, folder_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_storage_path ON documents (storage_path)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN (metadata)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents (filename)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_org_filename ON documents (organization_id, filename)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents (uploaded_by)")

    # === AUDIT LOGS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id VARCHAR(36) PRIMARY KEY,
            organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id VARCHAR(36),
            action VARCHAR(20) NOT NULL,
            entity_type VARCHAR(20) NOT NULL,
            entity_id VARCHAR(36) NOT NULL,
            details JSONB NOT NULL DEFAULT '{}',
            ip_address VARCHAR(45),
            session_id VARCHAR(36),
            user_agent VARCHAR(512),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_org_id ON audit_logs (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs (entity_type, entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_org_type_created ON audit_logs (organization_id, entity_type, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_org_user_created ON audit_logs (organization_id, user_id, created_at)")

    # === USAGE EVENTS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_events (
            id VARCHAR(36) PRIMARY KEY,
            organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id VARCHAR(36),
            request_id VARCHAR(64) UNIQUE,
            feature VARCHAR(50) NOT NULL,
            model VARCHAR(100) NOT NULL,
            provider VARCHAR(50) NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cached_tokens INTEGER DEFAULT 0,
            input_cost DECIMAL(12, 8) DEFAULT 0,
            output_cost DECIMAL(12, 8) DEFAULT 0,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_org_created ON usage_events (organization_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_org_feature ON usage_events (organization_id, feature)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_user ON usage_events (user_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_request_id ON usage_events (request_id)")

    # === USAGE DAILY SUMMARY ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_daily_summary (
            id VARCHAR(36) PRIMARY KEY,
            organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            total_requests INTEGER DEFAULT 0,
            total_input_tokens BIGINT DEFAULT 0,
            total_output_tokens BIGINT DEFAULT 0,
            total_tokens BIGINT DEFAULT 0,
            total_cost DECIMAL(12, 4) DEFAULT 0,
            feature_breakdown JSONB DEFAULT '{}',
            model_breakdown JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            UNIQUE (organization_id, date)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_usage_daily_org_date ON usage_daily_summary (organization_id, date)")

    # === USAGE LIMITS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_limits (
            id VARCHAR(36) PRIMARY KEY,
            organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
            monthly_token_limit BIGINT,
            monthly_request_limit INTEGER,
            credit_balance BIGINT DEFAULT 0,
            credit_used_this_period BIGINT DEFAULT 0,
            billing_cycle_start DATE,
            billing_cycle_end DATE,
            alert_threshold_percent INTEGER DEFAULT 80,
            alert_sent_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_usage_limits_org ON usage_limits (organization_id)")

    # === MODEL PRICING ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS model_pricing (
            id VARCHAR(36) PRIMARY KEY,
            provider VARCHAR(50) NOT NULL,
            model VARCHAR(100) NOT NULL,
            input_price_per_million DECIMAL(10, 4) NOT NULL,
            output_price_per_million DECIMAL(10, 4) NOT NULL,
            cached_price_per_million DECIMAL(10, 4) DEFAULT 0,
            effective_from DATE NOT NULL,
            effective_to DATE,
            UNIQUE (provider, model, effective_from)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_model_pricing_lookup ON model_pricing (provider, model, effective_from)")

    # Seed model pricing (current as of Dec 2024)
    op.execute("""
        INSERT INTO model_pricing (id, provider, model, input_price_per_million, output_price_per_million, cached_price_per_million, effective_from)
        VALUES
            (gen_random_uuid()::text, 'anthropic', 'claude-3-5-sonnet-20241022', 3.0, 15.0, 0.30, '2024-01-01'),
            (gen_random_uuid()::text, 'anthropic', 'claude-3-5-haiku-20241022', 1.0, 5.0, 0.10, '2024-01-01'),
            (gen_random_uuid()::text, 'anthropic', 'claude-3-opus-20240229', 15.0, 75.0, 1.50, '2024-01-01'),
            (gen_random_uuid()::text, 'openai', 'gpt-4o', 2.5, 10.0, 1.25, '2024-01-01'),
            (gen_random_uuid()::text, 'openai', 'gpt-4o-mini', 0.15, 0.6, 0.075, '2024-01-01'),
            (gen_random_uuid()::text, 'google', 'gemini-1.5-pro', 1.25, 5.0, 0.3125, '2024-01-01'),
            (gen_random_uuid()::text, 'google', 'gemini-1.5-flash', 0.075, 0.3, 0.01875, '2024-01-01')
        ON CONFLICT (provider, model, effective_from) DO NOTHING
    """)


def downgrade() -> None:
    # Drop tables in reverse order of dependencies
    op.execute("DROP TABLE IF EXISTS model_pricing CASCADE")
    op.execute("DROP TABLE IF EXISTS usage_limits CASCADE")
    op.execute("DROP TABLE IF EXISTS usage_daily_summary CASCADE")
    op.execute("DROP TABLE IF EXISTS usage_events CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
    op.execute("DROP TABLE IF EXISTS folders CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS organizations CASCADE")
    op.execute("DROP TABLE IF EXISTS subscription_plans CASCADE")
