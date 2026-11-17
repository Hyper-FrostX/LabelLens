from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ScanStatus
from app.models.user import utc_now

if TYPE_CHECKING:
    from app.models.catalog import Product
    from app.models.user import User


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (
        Index("ix_scans_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        index=True,
    )
    uploaded_image_path: Mapped[str | None] = mapped_column(String(2048))
    scan_status: Mapped[ScanStatus] = mapped_column(
        SAEnum(
            ScanStatus,
            values_callable=lambda enum_type: [item.value for item in enum_type],
            native_enum=False,
            create_constraint=True,
            name="scan_status_values",
        ),
        default=ScanStatus.UPLOADED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    user: Mapped["User | None"] = relationship(back_populates="scans")
    product: Mapped["Product | None"] = relationship()
    extracted_label: Mapped["ExtractedLabel | None"] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True,
    )
    analysis_reports: Mapped[list["AnalysisReport"]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AnalysisReport.created_at",
    )


class ExtractedLabel(Base):
    __tablename__ = "extracted_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    ocr_text: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    scan: Mapped[Scan] = relationship(back_populates="extracted_label")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"
    __table_args__ = (
        CheckConstraint(
            "health_score IS NULL OR (health_score >= 0 AND health_score <= 100)",
            name="health_score_percentage",
        ),
        Index("ix_analysis_reports_scan_created_at", "scan_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
    )
    health_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    analysis_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    scan: Mapped[Scan] = relationship(back_populates="analysis_reports")
    findings: Mapped[list["AnalysisFinding"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AnalysisFinding(Base):
    __tablename__ = "analysis_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(2048))

    report: Mapped[AnalysisReport] = relationship(back_populates="findings")
