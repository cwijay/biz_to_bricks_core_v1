"""Initial schema for biz2bricks_core

Creates all tables for:
- Core: organizations, users, folders
- Documents: documents, audit_logs
- Usage: usage_events, usage_daily_summaries, usage_limits, model_pricing, subscription_plans
- AI Module: processing_jobs, document_generations, user_preferences,
             conversation_summaries, memory_entries, file_search_stores, document_folders

Revision ID: 001
Revises:
Create Date: 2024-12-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # CORE TABLES
    # ==========================================================================

    # Organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("settings", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column("storage_used_bytes", sa.BigInteger, server_default="0", nullable=False),
        sa.Column("storage_limit_bytes", sa.BigInteger, server_default="10737418240", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_organizations_slug", "organizations", ["slug"])
    op.create_index("idx_organizations_name", "organizations", ["name"])

    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(20), server_default="viewer", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("settings", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('admin', 'member', 'viewer')", name="chk_users_role"),
    )
    op.create_index("idx_users_org_id", "users", ["organization_id"])
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_org_email", "users", ["organization_id", "email"], unique=True)

    # Folders table
    op.create_table(
        "folders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "parent_id",
            sa.String(36),
            sa.ForeignKey("folders.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_folders_org_id", "folders", ["organization_id"])
    op.create_index("idx_folders_parent_id", "folders", ["parent_id"])
    op.create_index("idx_folders_org_name", "folders", ["organization_id", "name"])

    # ==========================================================================
    # DOCUMENT TABLES
    # ==========================================================================

    # Documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "folder_id",
            sa.String(36),
            sa.ForeignKey("folders.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "uploaded_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("content_type", sa.String(100)),
        sa.Column("gcs_path", sa.Text, nullable=False),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("metadata", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_documents_org_id", "documents", ["organization_id"])
    op.create_index("idx_documents_folder_id", "documents", ["folder_id"])
    op.create_index("idx_documents_uploaded_by", "documents", ["uploaded_by"])
    op.create_index("idx_documents_file_name", "documents", ["file_name"])
    op.create_index("idx_documents_file_hash", "documents", ["file_hash"])
    op.create_index("idx_documents_org_folder", "documents", ["organization_id", "folder_id"])
    op.create_index(
        "idx_documents_org_not_deleted",
        "documents",
        ["organization_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Audit logs table (job_id FK added after processing_jobs is created)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(36)),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("details", postgresql.JSONB, nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("session_id", sa.String(36)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(100)),
        sa.Column("document_hash", sa.String(64)),
        sa.Column("file_name", sa.String(255)),
        sa.Column("job_id", postgresql.UUID(as_uuid=False)),  # FK added later
    )

    # ==========================================================================
    # USAGE TABLES
    # ==========================================================================

    # Usage events table
    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(36)),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100)),
        sa.Column("input_tokens", sa.Integer, server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer, server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer, server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), server_default="0", nullable=False),
        sa.Column("metadata", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_usage_events_org_id", "usage_events", ["organization_id"])
    op.create_index("idx_usage_events_user_id", "usage_events", ["user_id"])
    op.create_index("idx_usage_events_event_type", "usage_events", ["event_type"])
    op.create_index("idx_usage_events_created_at", "usage_events", ["created_at"])
    op.create_index(
        "idx_usage_events_org_created",
        "usage_events",
        ["organization_id", "created_at"],
    )

    # Usage daily summaries table
    op.create_table(
        "usage_daily_summaries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("total_events", sa.Integer, server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer, server_default="0", nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(10, 6), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "date", "event_type", name="uq_daily_summary_org_date_type"
        ),
    )
    op.create_index("idx_daily_summaries_org_id", "usage_daily_summaries", ["organization_id"])
    op.create_index("idx_daily_summaries_date", "usage_daily_summaries", ["date"])
    op.create_index(
        "idx_daily_summaries_org_date",
        "usage_daily_summaries",
        ["organization_id", "date"],
    )

    # Usage limits table
    op.create_table(
        "usage_limits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("monthly_token_limit", sa.BigInteger, server_default="1000000", nullable=False),
        sa.Column("monthly_cost_limit_usd", sa.Numeric(10, 2), server_default="100", nullable=False),
        sa.Column("storage_limit_bytes", sa.BigInteger, server_default="10737418240", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_usage_limits_org_id", "usage_limits", ["organization_id"])

    # Model pricing table
    op.create_table(
        "model_pricing",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_name", sa.String(100), nullable=False, unique=True),
        sa.Column("input_price_per_1k", sa.Numeric(10, 6), nullable=False),
        sa.Column("output_price_per_1k", sa.Numeric(10, 6), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_model_pricing_name", "model_pricing", ["model_name"])

    # Subscription plans table
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("monthly_token_limit", sa.BigInteger, nullable=False),
        sa.Column("monthly_cost_limit_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("storage_limit_bytes", sa.BigInteger, nullable=False),
        sa.Column("price_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("features", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_subscription_plans_name", "subscription_plans", ["name"])

    # ==========================================================================
    # AI MODULE TABLES
    # ==========================================================================

    # Processing jobs table
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("document_hash", sa.String(64), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("complexity", sa.String(20), server_default="normal", nullable=False),
        sa.Column("status", sa.String(20), server_default="processing", nullable=False),
        sa.Column(
            "started_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("cached", sa.Boolean, server_default="false", nullable=False),
        sa.Column("output_path", sa.Text),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("error_message", sa.Text),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="chk_processing_jobs_status",
        ),
    )
    op.create_index("idx_jobs_org_id", "processing_jobs", ["organization_id"])
    op.create_index("idx_jobs_document_hash", "processing_jobs", ["document_hash"])
    op.create_index("idx_jobs_file_name", "processing_jobs", ["file_name"])
    op.create_index("idx_jobs_started_at", "processing_jobs", ["started_at"])
    op.create_index("idx_jobs_status", "processing_jobs", ["status"])
    op.create_index(
        "idx_jobs_org_cache_lookup",
        "processing_jobs",
        ["organization_id", "document_hash", "model", "status"],
        postgresql_where=sa.text("status = 'completed'"),
    )

    # Now add FK constraint and indexes for audit_logs (depends on processing_jobs)
    op.create_foreign_key(
        "fk_audit_logs_job_id",
        "audit_logs",
        "processing_jobs",
        ["job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_audit_logs_org_id", "audit_logs", ["organization_id"])
    op.create_index("idx_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("idx_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"])
    op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index(
        "idx_audit_logs_org_type_created",
        "audit_logs",
        ["organization_id", "entity_type", "created_at"],
    )
    op.create_index(
        "idx_audit_logs_org_user_created",
        "audit_logs",
        ["organization_id", "user_id", "created_at"],
    )

    # Document generations table
    op.create_table(
        "document_generations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("document_hash", sa.String(64)),
        sa.Column("document_name", sa.String(255), nullable=False),
        sa.Column("source_path", sa.Text),
        sa.Column("generation_type", sa.String(50), nullable=False),
        sa.Column("content", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column("options", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("processing_time_ms", sa.Float),
        sa.Column("session_id", sa.String(100)),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "generation_type IN ('summary', 'faqs', 'questions', 'all')",
            name="chk_document_generations_type",
        ),
    )
    op.create_index("idx_generations_org_id", "document_generations", ["organization_id"])
    op.create_index("idx_generations_document_name", "document_generations", ["document_name"])
    op.create_index("idx_generations_created_at", "document_generations", ["created_at"])
    op.create_index("idx_generations_session", "document_generations", ["session_id"])
    op.create_index(
        "idx_generations_org_cache",
        "document_generations",
        ["organization_id", "document_name", "generation_type", "model"],
    )
    op.create_index(
        "idx_generations_content",
        "document_generations",
        ["content"],
        postgresql_using="gin",
    )

    # User preferences table
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.String(100), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("preferred_language", sa.String(10), server_default="en", nullable=False),
        sa.Column("preferred_summary_length", sa.Integer, server_default="500", nullable=False),
        sa.Column("preferred_faq_count", sa.Integer, server_default="5", nullable=False),
        sa.Column("preferred_question_count", sa.Integer, server_default="10", nullable=False),
        sa.Column("custom_settings", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_user_prefs_org_id", "user_preferences", ["organization_id"])
    op.create_index("idx_user_prefs_org_user", "user_preferences", ["organization_id", "user_id"])
    op.create_index("idx_user_prefs_updated", "user_preferences", ["updated_at"])

    # Conversation summaries table
    op.create_table(
        "conversation_summaries",
        sa.Column("session_id", sa.String(100), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("key_topics", postgresql.ARRAY(sa.Text), server_default="{}", nullable=False),
        sa.Column("documents_discussed", postgresql.ARRAY(sa.Text), server_default="{}", nullable=False),
        sa.Column("queries_count", sa.Integer, server_default="0", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "agent_type IN ('document', 'sheets')",
            name="chk_conversation_summaries_agent_type",
        ),
    )
    op.create_index("idx_summaries_org_id", "conversation_summaries", ["organization_id"])
    op.create_index("idx_summaries_org_user", "conversation_summaries", ["organization_id", "user_id"])
    op.create_index("idx_summaries_user_id", "conversation_summaries", ["user_id"])
    op.create_index("idx_summaries_user_agent", "conversation_summaries", ["user_id", "agent_type"])
    op.create_index("idx_summaries_created_at", "conversation_summaries", ["created_at"])

    # Memory entries table
    op.create_table(
        "memory_entries",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("namespace", sa.String(100), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("data", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "namespace", "key", name="uq_memory_org_namespace_key"),
    )
    op.create_index("idx_memory_org_id", "memory_entries", ["organization_id"])
    op.create_index("idx_memory_org_namespace", "memory_entries", ["organization_id", "namespace"])
    op.create_index("idx_memory_namespace", "memory_entries", ["namespace"])
    op.create_index("idx_memory_namespace_key", "memory_entries", ["namespace", "key"])
    op.create_index("idx_memory_data", "memory_entries", ["data"], postgresql_using="gin")

    # File search stores table
    op.create_table(
        "file_search_stores",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("gemini_store_id", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(512), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("gcp_project", sa.String(255)),
        sa.Column("active_documents_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("total_size_bytes", sa.BigInteger, server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'error')",
            name="chk_file_search_stores_status",
        ),
    )
    op.create_index("idx_file_stores_gemini_id", "file_search_stores", ["gemini_store_id"])
    op.create_index("idx_file_stores_display_name", "file_search_stores", ["display_name"])
    op.create_index("idx_file_stores_status", "file_search_stores", ["status"])

    # Document folders table
    op.create_table(
        "document_folders",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "store_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("file_search_stores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("folder_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column(
            "parent_folder_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("document_folders.id", ondelete="CASCADE"),
        ),
        sa.Column("document_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("total_size_bytes", sa.BigInteger, server_default="0", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "parent_folder_id", "folder_name", name="uq_folder_org_parent_name"
        ),
    )
    op.create_index("idx_doc_folders_org_id", "document_folders", ["organization_id"])
    op.create_index("idx_doc_folders_store_id", "document_folders", ["store_id"])
    op.create_index("idx_doc_folders_parent", "document_folders", ["parent_folder_id"])
    op.create_index("idx_doc_folders_name", "document_folders", ["folder_name"])
    op.create_index("idx_doc_folders_org_name", "document_folders", ["organization_id", "folder_name"])


def downgrade() -> None:
    # Drop tables in reverse order of creation (respecting foreign key dependencies)

    # Drop FK constraint from audit_logs first
    op.drop_constraint("fk_audit_logs_job_id", "audit_logs", type_="foreignkey")

    # AI Module tables
    op.drop_table("document_folders")
    op.drop_table("file_search_stores")
    op.drop_table("memory_entries")
    op.drop_table("conversation_summaries")
    op.drop_table("user_preferences")
    op.drop_table("document_generations")
    op.drop_table("processing_jobs")

    # Usage tables
    op.drop_table("subscription_plans")
    op.drop_table("model_pricing")
    op.drop_table("usage_limits")
    op.drop_table("usage_daily_summaries")
    op.drop_table("usage_events")

    # Document tables
    op.drop_table("audit_logs")
    op.drop_table("documents")

    # Core tables
    op.drop_table("folders")
    op.drop_table("users")
    op.drop_table("organizations")
