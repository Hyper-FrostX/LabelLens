import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LabelComplianceInput(BaseModel):
    label_text: str = Field(min_length=1, max_length=20000)
    product_category: str | None = Field(default=None, max_length=120)
    label_corrections: dict[str, Any] = Field(default_factory=dict, max_length=100)
    corrections_confirmed: bool = False
    extraction_metadata: dict[str, Any] | None = None
    symbol_review: Literal[
        "VEGETARIAN",
        "NON_VEGETARIAN",
        "REJECTED",
        "NEEDS_MANUAL_REVIEW",
    ] | None = None

    @field_validator("label_corrections", "extraction_metadata")
    @classmethod
    def validate_label_metadata_size(cls, value):
        if value is None:
            return value
        try:
            serialized = json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError("Label correction metadata must contain JSON values.") from error
        if len(serialized) > 50000:
            raise ValueError("Label correction metadata must be no larger than 50,000 characters.")
        return value


class LabelComplianceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    overall_status: str
    legal_compliance_determination: str
    product_information: dict[str, Any]
    fssai_license_information: dict[str, Any]
    mandatory_declarations: list[dict[str, Any]]
    ingredient_inspection: dict[str, Any]
    allergen_inspection: dict[str, Any]
    nutrition_inspection: dict[str, Any]
    date_inspection: dict[str, Any]
    vegetarian_declaration: dict[str, Any]
    potential_inconsistencies: list[dict[str, Any]]
    manual_review_requirements: list[dict[str, Any]]
    regulatory_rules: list[dict[str, Any]]
    regulatory_sources: list[dict[str, Any]]
    ocr_limitations: list[str]
    source_text: str
    original_ocr_text: str | None = None
    corrections_applied: bool = False
    user_corrections: dict[str, Any] | None = None
    image_extraction: dict[str, Any] | None = None
