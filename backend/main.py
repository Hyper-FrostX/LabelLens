
import math
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from app.services import label_ocr
from app.services.additive_detector import (
    ConcernLevel,
    detect_additives,
    get_curated_additives,
)
from app.services.gemini_vision import (
    extract_label_with_vision,
    generate_fallback_food_suggestions,
)
from app.services.ingredient_analysis import analyze_ingredients
from app.services.label_parser import parse_label_text, split_ingredients_text
from app.services.nutrition import (
    analyze_excess_nutrients,
    analyze_nutrition,
    calculate_health_score,
)

load_dotenv()


MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024


app = FastAPI(
    title="Label Lens API",
    description="AI-powered food label analysis and nutrition intelligence",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
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


class IngredientAnalysisInput(BaseModel):
    ingredients: list[str] | None = None
    ingredients_text: str | None = None


class LabelAnalysisInput(BaseModel):
    product_name: str | None = Field(default=None, max_length=200)
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
    food_suggestions: list[dict[str, Any]] | None = None
    dietary_advice: str | None = None

    @field_validator(
        "sugar_g",
        "added_sugar_g",
        "sodium_mg",
        "saturated_fat_g",
    )
    @classmethod
    def validate_finite_label_nutrients(
        cls,
        value: float | None,
    ) -> float | None:
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


@app.get("/additives/knowledge-base")
def knowledge_base_endpoint(
    concern_level: ConcernLevel | None = None,
    query: str | None = None,
):
    """Retrieve curated additives and ingredients with functional purpose and evidence."""
    additives = get_curated_additives(concern_level=concern_level, query=query)
    return {
        "total": len(additives),
        "additives": additives,
    }


@app.post("/analyze/nutrition")
def nutrition_endpoint(data: NutritionInput):
    return analyze_nutrition(
        sugar_g=data.sugar_g,
        sodium_mg=data.sodium_mg,
        saturated_fat_g=data.saturated_fat_g,
        basis=data.basis,
    )


@app.post("/analyze/ingredients")
def analyze_ingredients_endpoint(data: IngredientAnalysisInput):
    """Identify selected additives and ingredients from the curated knowledge base."""
    target = (
        data.ingredients
        if data.ingredients is not None
        else data.ingredients_text
    )
    return detect_additives(target)


@app.post("/analyze/label")
def label_analysis_endpoint(data: LabelAnalysisInput):
    ingredients = (
        split_ingredients_text(data.ingredients_text)
        if data.ingredients_text is not None
        else None
    )
    units = {
        "total_sugar": data.sugar_unit,
        "added_sugar": data.added_sugar_unit,
        "sodium": data.sodium_unit,
        "saturated_fat": data.saturated_fat_unit,
    }

    food_suggestions = data.food_suggestions
    dietary_advice = data.dietary_advice
    if not food_suggestions:
        food_suggestions, default_advice = generate_fallback_food_suggestions(
            product_name=data.product_name,
            nutrients={
                "sugar_g": data.sugar_g,
                "added_sugar_g": data.added_sugar_g,
                "sodium_mg": data.sodium_mg,
                "saturated_fat_g": data.saturated_fat_g,
            },
            ingredients_text=data.ingredients_text,
        )
        dietary_advice = dietary_advice or default_advice

    serving_size_text = data.serving_size_text
    if data.basis == "per_serving" and not (serving_size_text and serving_size_text.strip()):
        serving_size_text = "30 g"

    return {
        "product_name": data.product_name,
        "basis": data.basis,
        "excess_nutrients": analyze_excess_nutrients(
            sugar_g=data.sugar_g,
            added_sugar_g=data.added_sugar_g,
            sodium_mg=data.sodium_mg,
            saturated_fat_g=data.saturated_fat_g,
            basis=data.basis,
            units=units,
            serving_size_text=serving_size_text,
        ),
        "health_score": calculate_health_score(
            sugar_g=data.sugar_g,
            added_sugar_g=data.added_sugar_g,
            sodium_mg=data.sodium_mg,
            saturated_fat_g=data.saturated_fat_g,
            basis=data.basis,
            units=units,
            serving_size_text=serving_size_text,
        ),
        "ingredient_analysis": analyze_ingredients(
            ingredients,
            ingredients_available=data.ingredients_text is not None,
        ),
        "food_suggestions": food_suggestions,
        "dietary_advice": dietary_advice,
        "note": (
            "These project-defined nutrient references and curated "
            "ingredient notes are informational. They are not medical "
            "advice, official nutrition grades, or proof that a product "
            "is safe or unsafe."
        ),
    }


@app.post(
    "/extract/label",
    description=(
        "Extract label text, candidate nutrition fields, and food suggestions "
        "from one local image upload. Maximum upload size is 10 MiB."
    ),
)
async def extract_label_endpoint(file: UploadFile = File(...)):
    image_bytes = await file.read(MAX_IMAGE_UPLOAD_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds the 10 MiB upload limit.",
        )

    try:
        await run_in_threadpool(label_ocr.validate_image, image_bytes)
    except label_ocr.UnsupportedImageFormatError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except label_ocr.ImageTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except label_ocr.InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        parsed = await run_in_threadpool(extract_label_with_vision, image_bytes)
    except label_ocr.UnsupportedImageFormatError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except label_ocr.ImageTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except label_ocr.InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except label_ocr.OCRServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return parsed
