"""
Intelligence report models for business intelligence features.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Text, Integer, Date, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from biz2bricks_core.models.base import Base

if TYPE_CHECKING:
    from biz2bricks_core.models.core import OrganizationModel


class IntelligenceReportModel(Base):
    """
    Intelligence reports table for business intelligence features.

    Stores report metadata, status, and generated content for:
    - Expense summaries
    - Vendor analysis
    - Invoice reconciliation
    - Cash flow projections
    - Spend trends analysis
    - Tax preparation reports
    """

    __tablename__ = "intelligence_reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    folder_id: Mapped[str] = mapped_column(String(36), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )  # pending, extracting, aggregating, analyzing, generating, completed, failed

    # Date range for report filtering
    date_range_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_range_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Report options
    options: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Processing metrics
    document_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    extracted_record_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    # Generated content
    summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # Executive summary data
    insights: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True
    )  # LLM-generated insights
    charts: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True
    )  # Chart data and metadata

    # Output file paths (GCS)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    excel_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    json_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Performance tracking
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Creator tracking
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship()

    __table_args__ = (
        Index("idx_intelligence_reports_org_id", "organization_id"),
        Index("idx_intelligence_reports_folder_id", "folder_id"),
        Index("idx_intelligence_reports_status", "status"),
        Index("idx_intelligence_reports_report_type", "report_type"),
        Index("idx_intelligence_reports_created_at", "created_at"),
        Index(
            "idx_intelligence_reports_org_folder",
            "organization_id",
            "folder_id",
        ),
        Index(
            "idx_intelligence_reports_org_status",
            "organization_id",
            "status",
        ),
        Index(
            "idx_intelligence_reports_org_type",
            "organization_id",
            "report_type",
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "folder_id": self.folder_id,
            "report_type": self.report_type,
            "status": self.status,
            "date_range_start": (
                self.date_range_start.isoformat() if self.date_range_start else None
            ),
            "date_range_end": (
                self.date_range_end.isoformat() if self.date_range_end else None
            ),
            "options": self.options,
            "document_count": self.document_count,
            "extracted_record_count": self.extracted_record_count,
            "summary": self.summary,
            "insights": self.insights,
            "charts": self.charts,
            "pdf_path": self.pdf_path,
            "excel_path": self.excel_path,
            "json_path": self.json_path,
            "error_message": self.error_message,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "created_by": self.created_by,
        }


# Alias for convenience
IntelligenceReport = IntelligenceReportModel
