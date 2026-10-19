import math
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from app.services.nutrition import analyze_nutrition


app = FastAPI(
    title="Label Lens API",
    description="AI-powered food label analysis",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NutritionInput(BaseModel):
    sugar_g: float | None = Field(default=None, ge=0)
    sodium_mg: float | None = Field(default=None, ge=0)
    saturated_fat_g: float | None = Field(default=None, ge=0)
    basis: Literal["per_serving", "per_100g"]

    @field_validator("sugar_g", "sodium_mg", "saturated_fat_g")
    @classmethod
    def validate_finite_nutrients(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Nutrient values must be finite.")
        return value


@app.get("/")
def home():
    return {
        "message": "Label Lens API is running!",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/analyze/nutrition")
def nutrition_endpoint(data: NutritionInput):
    return analyze_nutrition(
        sugar_g=data.sugar_g,
        sodium_mg=data.sodium_mg,
        saturated_fat_g=data.saturated_fat_g,
        basis=data.basis,
    )
