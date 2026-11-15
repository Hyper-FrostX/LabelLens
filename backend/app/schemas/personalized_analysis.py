import math
import re
from typing import Any

from pydantic import BaseModel, Field, model_validator


_NUTRIENT_UNITS = {
    "sugar_g": "sugar_unit",
    "added_sugar_g": "added_sugar_unit",
    "sodium_mg": "sodium_unit",
    "saturated_fat_g": "saturated_fat_unit",
}


def _field_value(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def _field_unit(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("unit")
    return None


def _as_declaration_list(value: Any) -> Any:
    value = _field_value(value)
    if value is None or isinstance(value, list):
        return value
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,;]", value) if part.strip()]
    return value


class PersonalizedAnalysisInput(BaseModel):
    sugar_g: float | None = Field(default=None, ge=0)
    added_sugar_g: float | None = Field(default=None, ge=0)
    sodium_mg: float | None = Field(default=None, ge=0)
    saturated_fat_g: float | None = Field(default=None, ge=0)
    basis: str | None = Field(default=None, max_length=30)
    serving_size_text: str | None = Field(default=None, max_length=100)
    sugar_unit: str | None = Field(default=None, max_length=20)
    added_sugar_unit: str | None = Field(default=None, max_length=20)
    sodium_unit: str | None = Field(default=None, max_length=20)
    saturated_fat_unit: str | None = Field(default=None, max_length=20)
    ingredients_text: str | None = Field(default=None, max_length=20000)
    ingredients: list[str] | None = Field(default=None, max_length=500)
    allergens: list[str] | None = Field(default=None, max_length=100)
    may_contain: list[str] | None = Field(default=None, max_length=100)
    nutrients: dict[str, Any] | None = None
    extracted_fields: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_extracted_label(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        data = dict(value)
        extracted_fields = data.get("extracted_fields")
        if isinstance(extracted_fields, dict):
            for key, field_value in extracted_fields.items():
                data.setdefault(key, field_value)

        for key in ("basis", "serving_size_text", "ingredients_text", "ingredients"):
            if key in data:
                data[key] = _field_value(data[key])

        for key in ("allergens", "may_contain"):
            if key in data:
                data[key] = _as_declaration_list(data[key])

        nutrients = data.get("nutrients")
        if isinstance(nutrients, dict):
            for nutrient_name, unit_key in _NUTRIENT_UNITS.items():
                field_value = nutrients.get(nutrient_name)
                if field_value is None:
                    continue
                data.setdefault(nutrient_name, _field_value(field_value))
                if data.get(unit_key) is None:
                    data[unit_key] = _field_unit(field_value)
        return data

    @model_validator(mode="after")
    def validate_finite_nutrients(self):
        for name in (
            "sugar_g",
            "added_sugar_g",
            "sodium_mg",
            "saturated_fat_g",
        ):
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")
        if self.ingredients is not None and any(
            not isinstance(item, str) or not item.strip()
            for item in self.ingredients
        ):
            raise ValueError("Ingredient entries must be non-empty text.")
        for declaration_name in ("allergens", "may_contain"):
            declarations = getattr(self, declaration_name)
            if declarations is not None and any(
                not isinstance(item, str) or not item.strip()
                for item in declarations
            ):
                raise ValueError("Allergen declarations must be non-empty text.")
        return self
