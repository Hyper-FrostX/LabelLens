import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.models.enums import NutrientBasis
from app.schemas.common import ORMRead


class IngredientRead(ORMRead):
    id: int
    canonical_name: str
    description: str | None
    ingredient_type: str
    evidence_reference: str | None


class IngredientCreate(BaseModel):
    canonical_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    ingredient_type: str = Field(min_length=1, max_length=80)
    evidence_reference: str | None = Field(default=None, max_length=2048)


class ProductIngredientRead(ORMRead):
    product_id: int
    ingredient_id: int
    ingredient_order: int
    original_label_text: str
    ingredient: IngredientRead


class ProductIngredientCreate(BaseModel):
    ingredient_id: int = Field(gt=0)
    ingredient_order: int = Field(ge=0)
    original_label_text: str = Field(min_length=1)


class ProductNutrientRead(ORMRead):
    id: int
    product_id: int
    nutrient_name: str
    amount: Decimal
    unit: str
    basis: NutrientBasis


class ProductNutrientCreate(BaseModel):
    nutrient_name: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(ge=0)
    unit: str = Field(min_length=1, max_length=24)
    basis: NutrientBasis


class ProductRead(ORMRead):
    id: int
    product_name: str
    brand: str | None
    barcode: str | None
    category: str | None
    image_url: str | None
    serving_size_text: str | None
    ingredients_text: str | None
    declared_allergens: list[str] | None
    may_contain: list[str] | None
    source_name: str | None
    source_product_id: str | None
    source_url: str | None
    source_license: str | None
    source_updated_at: datetime | None
    created_at: datetime
    ingredients: list[ProductIngredientRead] = Field(default_factory=list)
    nutrients: list[ProductNutrientRead] = Field(default_factory=list)


class ProductCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=240)
    brand: str | None = Field(default=None, max_length=160)
    barcode: str | None = Field(default=None, max_length=32)
    category: str | None = Field(default=None, max_length=120)
    image_url: str | None = Field(default=None, max_length=2048)
    ingredients: list[ProductIngredientCreate] = Field(default_factory=list)
    nutrients: list[ProductNutrientCreate] = Field(default_factory=list)


_IMPORT_NUTRIENT_UNITS = {
    "energy": {"kcal", "kj"},
    "total_fat": {"g", "mg"},
    "saturated_fat": {"g", "mg"},
    "trans_fat": {"g", "mg"},
    "carbohydrates": {"g", "mg"},
    "sugar": {"g", "mg"},
    "added_sugar": {"g", "mg"},
    "protein": {"g", "mg"},
    "fiber": {"g", "mg"},
    "sodium": {"mg", "g"},
}
_IMPORT_NUTRIENT_ALIASES = {
    "calories": "energy",
    "total_sugar": "sugar",
    "fibre": "fiber",
}


class ProductImportNutrient(BaseModel):
    nutrient_name: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(ge=0)
    unit: str = Field(min_length=1, max_length=24)
    basis: NutrientBasis

    @field_validator("amount")
    @classmethod
    def require_finite_amount(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Imported nutrient values must be finite.")
        return value

    @field_validator("nutrient_name")
    @classmethod
    def normalize_nutrient_name(cls, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
        normalized = _IMPORT_NUTRIENT_ALIASES.get(normalized, normalized)
        if normalized not in _IMPORT_NUTRIENT_UNITS:
            raise ValueError("Nutrient name is not supported for normalized comparison.")
        return normalized

    @field_validator("unit")
    @classmethod
    def normalize_nutrient_unit(cls, value: str) -> str:
        return value.casefold().strip()

    @model_validator(mode="after")
    def require_recognized_unit(self):
        if self.unit not in _IMPORT_NUTRIENT_UNITS[self.nutrient_name]:
            raise ValueError(
                f"Unit {self.unit!r} is not supported for {self.nutrient_name}."
            )
        return self


class ProductImportInput(BaseModel):
    product_name: str = Field(min_length=1, max_length=240)
    brand: str | None = Field(default=None, max_length=160)
    barcode: str | None = Field(default=None, max_length=32)
    category: str | None = Field(default=None, max_length=120)
    image_url: HttpUrl | None = None
    serving_size_text: str | None = Field(default=None, max_length=120)
    ingredients_text: str | None = Field(default=None, max_length=20_000)
    declared_allergens: list[str] | None = Field(default=None, max_length=50)
    may_contain: list[str] | None = Field(default=None, max_length=50)
    nutrients: list[ProductImportNutrient] = Field(default_factory=list, max_length=100)
    source_name: str = Field(min_length=1, max_length=240)
    source_product_id: str = Field(min_length=1, max_length=240)
    source_url: HttpUrl
    source_license: str = Field(min_length=1, max_length=240)
    source_updated_at: datetime | None = None

    @field_validator("product_name", "source_name", "source_product_id", "source_license")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This value must not be blank.")
        return normalized

    @field_validator("barcode")
    @classmethod
    def validate_barcode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not re.fullmatch(r"\d{8,14}", normalized):
            raise ValueError("Product barcode must contain 8-14 digits.")
        if len(normalized) not in {8, 12, 13, 14}:
            raise ValueError("Product barcode must use a supported GTIN length.")
        digits = [int(digit) for digit in normalized]
        checksum = sum(
            digit * (3 if offset % 2 == 0 else 1)
            for offset, digit in enumerate(reversed(digits[:-1]))
        )
        if (10 - checksum % 10) % 10 != digits[-1]:
            raise ValueError("Product barcode check digit is invalid.")
        return normalized

    @field_validator("declared_allergens", "may_contain")
    @classmethod
    def normalize_declarations(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = list(dict.fromkeys(item.strip() for item in values if item.strip()))
        return normalized

    @model_validator(mode="after")
    def require_unique_nutrients(self):
        keys = [(item.nutrient_name, item.basis) for item in self.nutrients]
        if len(set(keys)) != len(keys):
            raise ValueError("Imported nutrient names and bases must be unique.")
        return self
