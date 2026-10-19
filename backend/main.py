import math
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from app.services import label_ocr
from app.services.label_parser import parse_label_text
from app.services.nutrition import analyze_nutrition


MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024


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


@app.post(
    "/extract/label",
    description=(
        "Extract label text and candidate nutrition fields from one local "
        "image upload. Maximum upload size is 10 MiB."
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
        ocr_text = await run_in_threadpool(label_ocr.extract_text, image_bytes)
    except label_ocr.OCRServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return parse_label_text(ocr_text)
