from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

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
