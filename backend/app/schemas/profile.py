import math
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import ExpertiseLevel


class HealthConditionChoice(str, Enum):
    DIABETES = "Diabetes"
    HYPERTENSION = "Hypertension"
    HIGH_CHOLESTEROL = "High Cholesterol"
    HEART_HEALTH_CONCERNS = "Heart Health Concerns"
    KIDNEY_HEALTH_CONCERNS = "Kidney Health Concerns"
    OBESITY_WEIGHT_MANAGEMENT = "Obesity / Weight Management"
    THYROID_DIETARY_CONCERNS = "Thyroid-related Dietary Concerns"
    CELIAC_DISEASE = "Celiac disease"
    PKU = "PKU"
    IBS = "IBS"
    GOUT = "Gout"
    HEART_DISEASE = "Heart disease"
    KIDNEY_DISEASE = "Kidney disease"


class AllergenChoice(str, Enum):
    GLUTEN = "Gluten"
    DAIRY = "Dairy"
    WHEAT = "Wheat"
    SOY = "Soy"
    TREE_NUTS = "Tree nuts"
    PEANUTS = "Peanuts"
    EGGS = "Eggs"
    FISH = "Fish"
    SHELLFISH = "Shellfish"
    SESAME = "Sesame"


class DietaryPreference(str, Enum):
    VEGETARIAN = "Vegetarian"
    VEGAN = "Vegan"
    GLUTEN_FREE = "Gluten-free"
    DAIRY_FREE = "Dairy-free"


class NutritionGoal(str, Enum):
    HIGHER_PROTEIN = "higher_protein"
    HIGHER_FIBER = "higher_fiber"
    LOWER_SUGAR = "lower_sugar"
    LOWER_SODIUM = "lower_sodium"
    LOWER_SATURATED_FAT = "lower_saturated_fat"
    LOWER_CALORIES = "lower_calories"


def _normalize_choices(
    value: Any,
    choice_type: type[Enum],
    label: str,
) -> Any:
    if not isinstance(value, (list, tuple)):
        return value
    allowed = {choice.value.casefold(): choice.value for choice in choice_type}
    normalized = []
    seen = set()
    for selection in value:
        name = selection.value if isinstance(selection, choice_type) else selection
        if not isinstance(name, str):
            raise ValueError(f"Unsupported {label} value.")
        canonical = allowed.get(name.strip().casefold())
        if canonical is None:
            raise ValueError(f"Unsupported {label} value.")
        key = canonical.casefold()
        if key not in seen:
            normalized.append(canonical)
            seen.add(key)
    return normalized


class HealthProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    expertise_level: ExpertiseLevel
    health_conditions: list[HealthConditionChoice] = Field(max_length=15)
    allergens: list[AllergenChoice] = Field(max_length=10)
    custom_allergens: list[str] = Field(max_length=20)
    dietary_preferences: list[DietaryPreference] = Field(
        default_factory=list,
        max_length=4,
    )
    ingredient_exclusions: list[str] = Field(default_factory=list, max_length=20)
    nutrition_goals: list[NutritionGoal] = Field(default_factory=list, max_length=6)
    calorie_goal_kcal: float | None = Field(default=None, ge=500, le=10000)
    protein_goal_g: float | None = Field(default=None, ge=1, le=400)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be blank.")
        return normalized

    @field_validator("expertise_level", mode="before")
    @classmethod
    def normalize_expertise_level(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().casefold()
        return value

    @field_validator("health_conditions", mode="before")
    @classmethod
    def normalize_health_conditions(cls, value) -> list[str]:
        return _normalize_choices(value, HealthConditionChoice, "health condition")

    @field_validator("allergens", mode="before")
    @classmethod
    def normalize_allergens(cls, value) -> list[str]:
        return _normalize_choices(value, AllergenChoice, "allergen")

    @field_validator("custom_allergens")
    @classmethod
    def normalize_custom_allergens(cls, values: list[str]) -> list[str]:
        normalized = []
        seen = set()
        for value in values:
            name = value.strip()
            if not name or len(name) > 120:
                raise ValueError("Custom allergen names must be 1-120 characters.")
            key = name.casefold()
            if key not in seen:
                normalized.append(name)
                seen.add(key)
        return normalized

    @field_validator("dietary_preferences", mode="before")
    @classmethod
    def normalize_dietary_preferences(cls, value) -> list[str]:
        return _normalize_choices(value, DietaryPreference, "dietary preference")

    @field_validator("nutrition_goals", mode="before")
    @classmethod
    def normalize_nutrition_goals(cls, value) -> list[str]:
        return _normalize_choices(value, NutritionGoal, "nutrition goal")

    @field_validator("ingredient_exclusions")
    @classmethod
    def normalize_ingredient_exclusions(cls, values: list[str]) -> list[str]:
        normalized = []
        seen = set()
        for value in values:
            name = value.strip()
            if not name or len(name) > 120:
                raise ValueError("Ingredient exclusions must be 1-120 characters.")
            if name.casefold() not in seen:
                normalized.append(name)
                seen.add(name.casefold())
        return normalized

    @field_validator("calorie_goal_kcal", "protein_goal_g")
    @classmethod
    def validate_finite_daily_targets(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Daily nutrition targets must be finite.")
        return value

    @model_validator(mode="after")
    def reject_standard_allergens_as_custom(self):
        standard_names = {choice.value.casefold() for choice in AllergenChoice}
        if any(name.casefold() in standard_names for name in self.custom_allergens):
            raise ValueError(
                "Use the standard allergens list for supported allergens."
            )
        return self


class HealthProfileResponse(BaseModel):
    name: str
    expertise_level: ExpertiseLevel
    health_conditions: list[HealthConditionChoice]
    allergens: list[AllergenChoice]
    custom_allergens: list[str]
    dietary_preferences: list[DietaryPreference]
    ingredient_exclusions: list[str]
    nutrition_goals: list[NutritionGoal]
    calorie_goal_kcal: float | None
    protein_goal_g: float | None
    updated_at: datetime
