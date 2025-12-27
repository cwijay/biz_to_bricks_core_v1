"""
SQLAlchemy models for RAG (Retrieval-Augmented Generation) caching.

Tables:
- rag_query_cache: Semantic cache for RAG queries using pgvector
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

# Try to import pgvector, fall back gracefully if not available
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None

from biz2bricks_core.models.base import Base


class RAGQueryCacheModel(Base):
    """
    Semantic cache for RAG queries using pgvector.

    Stores query embeddings and responses for semantic similarity matching.
    Enables cache hits for semantically similar queries (e.g., "who wrote this?"
    matches "who is the author?") to reduce LLM and vector search costs.
    """
    __tablename__ = "rag_query_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Note: organizations.id is VARCHAR, not UUID
    org_id = Column(String(255), ForeignKey("organizations.id"), nullable=False, index=True)

    # Query and embedding
    query_text = Column(Text, nullable=False)
    # Gemini text-embedding-004 produces 768-dimensional embeddings
    query_embedding = Column(Vector(768), nullable=False) if PGVECTOR_AVAILABLE else Column(Text)

    # Cached response
    answer = Column(Text, nullable=False)
    citations = Column(JSONB)  # Store citations as JSON array

    # Search context (for scoped cache matching)
    folder_filter = Column(String(255), nullable=True)
    file_filter = Column(String(255), nullable=True)
    search_mode = Column(String(50), default="hybrid")

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    hit_count = Column(Integer, default=0)  # Track cache usage

    # Filter indexes for scoped queries
    # Note: Vector index should be created manually after pgvector is enabled:
    # CREATE INDEX idx_rag_cache_embedding ON rag_query_cache
    #   USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 100);
    __table_args__ = (
        Index('idx_rag_cache_org_folder', 'org_id', 'folder_filter'),
        Index('idx_rag_cache_org_file', 'org_id', 'file_filter'),
    )

    def __repr__(self):
        return f"<RAGQueryCache(id={self.id}, query='{self.query_text[:50]}...')>"


# Backwards-compatible alias
RAGQueryCache = RAGQueryCacheModel

__all__ = [
    "RAGQueryCacheModel",
    "RAGQueryCache",
    "PGVECTOR_AVAILABLE",
]
