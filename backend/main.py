
import math
from typing import Literal

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.auth import router as auth_router
from app.api.personalized_analysis import router as personalized_analysis_router
from app.api.profile import router as profile_router
from app.database.config import get_optional_db
from app.repositories.ingredient_knowledge_repository import IngredientKnowledgeRepository
from app.services import label_ocr
from app.services.additive_detector import (
    ConcernLevel,
    detect_additives,
    get_curated_additives,
)
from app.services.label_analysis import analyze_label
from app.services.ingredient_analysis import analyze_ingredients
from app.services.label_parser import parse_label_text, split_ingredients_text
from app.services.nutrition import analyze_nutrition


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

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(personalized_analysis_router)


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
def analyze_ingredients_endpoint(
    data: IngredientAnalysisInput,
    session: Session | None = Depends(get_optional_db),
):
    """Identify selected additives and ingredients from the curated knowledge base."""
    target = (
        data.ingredients
        if data.ingredients is not None
        else data.ingredients_text
    )
    legacy_analysis = detect_additives(target)
    ingredients = (
        target
        if isinstance(target, list)
        else split_ingredients_text(target)
        if target is not None
        else None
    )
    knowledge_records = (
        IngredientKnowledgeRepository.load_catalog(session)
        if session is not None
        else None
    )
    legacy_analysis["ingredient_analysis"] = analyze_ingredients(
        ingredients,
        ingredients_available=target is not None,
        knowledge_records=knowledge_records,
    )
    return legacy_analysis


@app.post("/analyze/label")
def label_analysis_endpoint(
    data: LabelAnalysisInput,
    session: Session | None = Depends(get_optional_db),
):
    knowledge_records = (
        IngredientKnowledgeRepository.load_catalog(session)
        if session is not None
        else None
    )
    return analyze_label(data, knowledge_records=knowledge_records)


@app.post(
    "/extract/label",
    description=(
        "Extract label text and candidate nutrition fields from one local "
        "image upload. Maximum upload size is 10 MiB."
    ),
)
async def extract_label_endpoint(
    file: UploadFile = File(...),
    session: Session | None = Depends(get_optional_db),
):
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
        ocr_text = await run_in_threadpool(label_ocr.extract_text, image_bytes)
    except label_ocr.OCRServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    parsed = parse_label_text(ocr_text)
    ingredient_target = parsed.get("ingredients") or parsed.get("ingredients_text")
    parsed["additive_analysis"] = detect_additives(ingredient_target)
    knowledge_records = (
        IngredientKnowledgeRepository.load_catalog(session)
        if session is not None
        else None
    )
    extracted_ingredients = parsed.get("ingredients")
    if extracted_ingredients is None and parsed.get("ingredients_text") is not None:
        extracted_ingredients = split_ingredients_text(parsed["ingredients_text"])
    parsed["ingredient_analysis"] = analyze_ingredients(
        extracted_ingredients,
        ingredients_available=ingredient_target is not None,
        knowledge_records=knowledge_records,
    )
    return parsed
