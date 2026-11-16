import json
import math
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.personalized_analysis import PersonalizedAnalysisInput


class AdditionalNutrientInput(BaseModel):
    value: float | None = Field(default=None, ge=0)
    unit: str = Field(min_length=1, max_length=20)

    @field_validator("value")
    @classmethod
    def validate_finite_value(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Additional nutrient values must be finite.")
        return value


class ProductAnalysisInput(PersonalizedAnalysisInput):
    product_name: str | None = Field(default=None, max_length=200)
    product_category: str | None = Field(default=None, max_length=120)
    label_text: str | None = Field(default=None, max_length=20000)
    label_corrections: dict[str, Any] = Field(default_factory=dict, max_length=100)
    corrections_confirmed: bool = False
    extraction_metadata: dict[str, Any] | None = None
    symbol_review: Literal[
        "VEGETARIAN",
        "NON_VEGETARIAN",
        "REJECTED",
        "NEEDS_MANUAL_REVIEW",
    ] | None = None
    explanation_level: Literal["brief", "standard", "detailed"] = "standard"
    recommendation_goal: Literal[
        "balanced",
        "lower_sugar",
        "lower_sodium",
        "lower_saturated_fat",
        "higher_protein",
        "higher_fiber",
        "lower_calories",
    ] = "balanced"
    save_to_history: bool = False
    additional_nutrients: dict[str, AdditionalNutrientInput] = Field(
        default_factory=dict,
        max_length=50,
    )

    @field_validator("product_name")
    @classmethod
    def normalize_product_name(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("additional_nutrients")
    @classmethod
    def validate_additional_nutrient_names(
        cls,
        value: dict[str, AdditionalNutrientInput],
    ) -> dict[str, AdditionalNutrientInput]:
        if any(not name.strip() or len(name) > 80 for name in value):
            raise ValueError("Additional nutrient names must be 1-80 characters.")
        return value

    @field_validator("label_corrections", "extraction_metadata")
    @classmethod
    def validate_label_metadata_size(cls, value):
        if value is None:
            return value
        try:
            serialized = json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError("Label correction metadata must contain JSON values.") from error
        if len(serialized) > 50_000:
            raise ValueError("Label correction metadata must be no larger than 50,000 characters.")
        return value


class ProductQuestionInput(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    context: dict[str, Any] = Field(default_factory=dict)
    explanation_level: Literal["brief", "standard", "detailed"] = "standard"

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank.")
        return value

    @field_validator("context")
    @classmethod
    def limit_context_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            serialized = json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError("Context must contain JSON-compatible values.") from error
        if len(serialized) > 50_000:
            raise ValueError("Context must be no larger than 50,000 characters.")
        return value
