from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ScanStatus
from app.schemas.common import ORMRead


class ScanCreate(BaseModel):
    product_id: int | None = Field(default=None, gt=0)
    uploaded_image_path: str | None = Field(default=None, max_length=2048)


class ExtractedLabelCreate(BaseModel):
    extracted_data: dict[str, Any]
    ocr_text: str
    extraction_version: str = Field(min_length=1, max_length=64)


class ExtractedLabelRead(ORMRead):
    id: int
    scan_id: int
    extracted_data: dict[str, Any]
    ocr_text: str
    extraction_version: str
    created_at: datetime


class AnalysisFindingCreate(BaseModel):
    finding_type: str = Field(min_length=1, max_length=80)
    severity: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=240)
    description: str
    evidence_reference: str | None = Field(default=None, max_length=2048)


class AnalysisFindingRead(ORMRead):
    id: int
    report_id: int
    finding_type: str
    severity: str
    title: str
    description: str
    evidence_reference: str | None


class AnalysisReportCreate(BaseModel):
    health_score: Decimal | None = Field(default=None, ge=0, le=100)
    analysis_data: dict[str, Any]
    scoring_version: str = Field(min_length=1, max_length=64)
    findings: list[AnalysisFindingCreate] = Field(default_factory=list)


class AnalysisReportRead(ORMRead):
    id: int
    scan_id: int
    health_score: Decimal | None
    analysis_data: dict[str, Any]
    scoring_version: str
    created_at: datetime
    findings: list[AnalysisFindingRead]


class ScanRead(ORMRead):
    id: int
    user_id: int | None
    product_id: int | None
    uploaded_image_path: str | None
    scan_status: ScanStatus
    created_at: datetime
    extracted_label: ExtractedLabelRead | None
    analysis_reports: list[AnalysisReportRead]
