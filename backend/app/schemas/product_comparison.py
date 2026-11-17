from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProductComparisonInput(BaseModel):
    scan_ids: list[int] = Field(min_length=2, max_length=5)
    recommendation_goal: Literal[
        "balanced",
        "lower_sugar",
        "lower_sodium",
        "lower_saturated_fat",
        "higher_protein",
        "higher_fiber",
        "lower_calories",
    ] = "balanced"

    @field_validator("scan_ids")
    @classmethod
    def require_unique_positive_ids(cls, values: list[int]) -> list[int]:
        if any(value < 1 for value in values):
            raise ValueError("Saved scan ids must be positive.")
        if len(set(values)) != len(values):
            raise ValueError("Choose each saved scan only once.")
        return values
