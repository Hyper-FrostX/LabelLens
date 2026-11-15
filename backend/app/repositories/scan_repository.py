from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisFinding, AnalysisReport, ExtractedLabel, Scan, ScanStatus
from app.schemas.scans import (
    AnalysisReportCreate,
    ExtractedLabelCreate,
    ScanCreate,
)


class ScanRepository:
    @staticmethod
    def create_for_user(
        session: Session,
        *,
        user_id: int,
        data: ScanCreate,
    ) -> Scan:
        if not isinstance(user_id, int) or user_id < 1:
            raise ValueError("A positive authenticated user id is required.")
        scan = Scan(
            user_id=user_id,
            product_id=data.product_id,
            uploaded_image_path=data.uploaded_image_path,
            scan_status=ScanStatus.UPLOADED,
        )
        session.add(scan)
        session.flush()
        return scan

    @staticmethod
    def get_for_user(
        session: Session,
        *,
        scan_id: int,
        user_id: int,
    ) -> Scan | None:
        return session.scalar(
            select(Scan).where(Scan.id == scan_id, Scan.user_id == user_id)
        )

    @staticmethod
    def list_for_user(
        session: Session,
        *,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Scan]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("offset must not be negative")
        return list(
            session.scalars(
                select(Scan)
                .where(Scan.user_id == user_id)
                .order_by(Scan.created_at.desc(), Scan.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )

    @classmethod
    def save_extracted_label(
        cls,
        session: Session,
        *,
        scan_id: int,
        user_id: int,
        data: ExtractedLabelCreate,
    ) -> ExtractedLabel:
        scan = cls.get_for_user(session, scan_id=scan_id, user_id=user_id)
        if scan is None:
            raise LookupError("Scan was not found for this user.")
        extracted_label = ExtractedLabel(
            scan_id=scan.id,
            extracted_data=data.extracted_data,
            ocr_text=data.ocr_text,
            extraction_version=data.extraction_version,
        )
        session.add(extracted_label)
        session.flush()
        return extracted_label

    @classmethod
    def add_analysis_report(
        cls,
        session: Session,
        *,
        scan_id: int,
        user_id: int,
        data: AnalysisReportCreate,
    ) -> AnalysisReport:
        scan = cls.get_for_user(session, scan_id=scan_id, user_id=user_id)
        if scan is None:
            raise LookupError("Scan was not found for this user.")
        report = AnalysisReport(
            scan_id=scan.id,
            health_score=data.health_score,
            analysis_data=data.analysis_data,
            scoring_version=data.scoring_version,
            findings=[
                AnalysisFinding(**finding.model_dump())
                for finding in data.findings
            ],
        )
        session.add(report)
        session.flush()
        return report
