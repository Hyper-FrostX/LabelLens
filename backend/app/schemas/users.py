from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ExpertiseLevel
from app.schemas.common import ORMRead


class HealthProfileCreate(BaseModel):
    expertise_level: ExpertiseLevel = ExpertiseLevel.BEGINNER


class UserRead(ORMRead):
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: datetime


class HealthProfileRead(ORMRead):
    id: int
    user_id: int
    expertise_level: ExpertiseLevel
    created_at: datetime
    updated_at: datetime


class HealthConditionRead(ORMRead):
    id: int
    name: str
    description: str | None


class HealthConditionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class UserHealthConditionRead(ORMRead):
    user_id: int
    condition_id: int


class UserHealthConditionCreate(BaseModel):
    condition_id: int = Field(gt=0)


class AllergenRead(ORMRead):
    id: int
    name: str
    category: str


class AllergenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)


class UserAllergenRead(ORMRead):
    id: int
    user_id: int
    allergen_id: int | None
    custom_allergen_name: str | None


class UserAllergenCreate(BaseModel):
    allergen_id: int | None = Field(default=None, gt=0)
    custom_allergen_name: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def require_catalog_or_custom_allergen(self):
        if self.allergen_id is None and not (
            self.custom_allergen_name and self.custom_allergen_name.strip()
        ):
            raise ValueError("Select a catalog allergen or provide a custom name.")
        return self
