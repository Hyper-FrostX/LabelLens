
import math
import os
from typing import Any, Literal

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.auth import router as auth_router
from app.api.personalized_analysis import router as personalized_analysis_router
from app.api.profile import router as profile_router
from app.database.config import get_db, get_optional_db
from app.models import AnalysisReport, Scan, User
from app.models.enums import ScanStatus
from app.repositories.ingredient_knowledge_repository import (
    IngredientKnowledgeRepository,
)
from app.repositories.product_repository import ProductRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.scan_repository import ScanRepository
from app.schemas.label_compliance import (
    LabelComplianceInput,
    LabelComplianceReport,
)
from app.schemas.product_analysis import ProductAnalysisInput, ProductQuestionInput
from app.schemas.scans import (
    AnalysisReportCreate,
    ExtractedLabelCreate,
    ScanCreate,
    ScanRead,
)
from app.security.cors import load_cors_settings
from app.security.dependencies import get_current_user, get_optional_current_user
from app.security.rate_limit import (
    RequestRateLimiter,
    load_rate_limit_policies,
)
from app.services import label_ocr
from app.services.additive_detector import (
    ConcernLevel,
    detect_additives,
    get_curated_additives,
)
from app.services.gemini_vision import (
    extract_label_with_vision,
    generate_fallback_food_suggestions,
    get_gemini_api_key,
)
from app.services.ingredient_analysis import analyze_ingredients
from app.services.label_analysis import analyze_label
from app.services.label_compliance import analyze_label_compliance
from app.services.label_parser import parse_label_text, split_ingredients_text
from app.services.nutrition import analyze_nutrition
from app.services.product_analysis import analyze_product, answer_product_question
from app.services.product_assistant import ask_product_question

MAX_IMAGE_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_INGREDIENT_TEXT_LENGTH = 10_000
MAX_INGREDIENT_LIST_ITEMS = 500
request_rate_limiter = RequestRateLimiter(load_rate_limit_policies())


app = FastAPI(
    title="Label Lens API",
    description="Food label analysis and nutrition intelligence",
    version="0.3.0",
)

cors_allowed_origins, cors_allow_credentials = load_cors_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_credentials=cors_allow_credentials,
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
    basis: Literal["per_serving", "per_100g", "per_100ml"]

    @field_validator("sugar_g", "sodium_mg", "saturated_fat_g")
    @classmethod
    def validate_finite_nutrients(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Nutrient values must be finite.")
        return value


class IngredientAnalysisInput(BaseModel):
    ingredients: list[str] | None = Field(
        default=None,
        max_length=MAX_INGREDIENT_LIST_ITEMS,
    )
    ingredients_text: str | None = Field(
        default=None,
        max_length=MAX_INGREDIENT_TEXT_LENGTH,
    )

    @field_validator("ingredients")
    @classmethod
    def validate_ingredient_entries(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        if sum(len(value) for value in values) > MAX_INGREDIENT_TEXT_LENGTH:
            raise ValueError("Ingredient text must be 10,000 characters or fewer.")
        if any(
            not value.strip() or not any(char.isalnum() for char in value)
            for value in values
        ):
            raise ValueError("Each ingredient must contain letters or numbers.")
        return values

    @field_validator("ingredients_text")
    @classmethod
    def validate_ingredient_text(cls, value: str | None) -> str | None:
        if value is not None and value.strip() and not any(
            char.isalnum() for char in value
        ):
            raise ValueError("Ingredient text must contain letters or numbers.")
        return value

    @model_validator(mode="after")
    def require_ingredient_content(self):
        if (
            not (self.ingredients_text and self.ingredients_text.strip())
            and not self.ingredients
        ):
            raise ValueError("Provide ingredient text or a non-empty ingredient list.")
        return self


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
    food_suggestions: list[dict[str, Any]] | None = Field(
        default=None,
        max_length=20,
    )
    dietary_advice: str | None = Field(default=None, max_length=2000)

    @field_validator("basis", mode="before")
    @classmethod
    def validate_or_clear_uncertain_basis(cls, value):
        if value is None:
            return value
        if not isinstance(value, str):
            raise ValueError("Unsupported nutrient basis.")
        if value in {"per_serving", "per_100g", "per_100ml"}:
            return value
        if any(
            marker in value.casefold()
            for marker in ("maybe", "not sure", "uncertain", "ambiguous", "unknown")
        ):
            return None
        raise ValueError("Unsupported nutrient basis.")

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


def enforce_request_rate_limit(request: Request, operation: str) -> None:
    client = request.client.host if request.client is not None else "unknown"
    retry_after = request_rate_limiter.check(operation, client)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )


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


@app.post("/analyze/product")
def product_analysis_endpoint(
    data: ProductAnalysisInput,
    session: Session | None = Depends(get_optional_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    knowledge_records = (
        IngredientKnowledgeRepository.load_catalog(session)
        if session is not None
        else None
    )
    if current_user is not None and session is not None:
        current_user = ProfileRepository.get_for_user(session, current_user.id)
    stored_products = ProductRepository.list_with_nutrients(session) if session else []
    if session is not None and current_user is not None:
        saved_reports = session.scalars(
            select(AnalysisReport.analysis_data)
            .join(Scan, Scan.id == AnalysisReport.scan_id)
            .where(Scan.user_id == current_user.id)
            .order_by(AnalysisReport.created_at.desc())
            .limit(50)
        ).all()
        stored_products.extend(saved_reports)
    result = analyze_product(
        data,
        knowledge_records=knowledge_records,
        current_user=current_user,
        stored_products=stored_products,
    )
    result["compliance_report"] = analyze_label_compliance(
        data.label_text or "",
        product_category=data.product_category,
        knowledge_records=knowledge_records,
        label_corrections=data.label_corrections,
        corrections_confirmed=data.corrections_confirmed,
        extraction_metadata=data.extraction_metadata,
        symbol_review=data.symbol_review,
    )
    if data.save_to_history:
        if current_user is None or session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sign in to save this analysis to your scan history.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        scan = ScanRepository.create_for_user(
            session,
            user_id=current_user.id,
            data=ScanCreate(),
        )
        scan.scan_status = ScanStatus.COMPLETED
        ScanRepository.save_extracted_label(
            session,
            scan_id=scan.id,
            user_id=current_user.id,
            data=ExtractedLabelCreate(
                extracted_data=data.model_dump(
                    mode="json",
                    exclude={"save_to_history"},
                ),
                ocr_text=data.label_text or data.ingredients_text or "",
                extraction_version="reviewed-product-analysis-v1",
            ),
        )
        score = result["nutrition"]["health_score"]
        ScanRepository.add_analysis_report(
            session,
            scan_id=scan.id,
            user_id=current_user.id,
            data=AnalysisReportCreate(
                health_score=score["score"]
                if score["status"] == "available"
                else None,
                analysis_data={
                    "product_report": result,
                    "input": data.model_dump(
                        mode="json",
                        exclude={"save_to_history"},
                    ),
                },
                scoring_version=(
                    "label-lens-nutrition-v1"
                    if score["status"] == "available"
                    else "unavailable"
                ),
            ),
        )
        session.commit()
        result["saved_scan_id"] = scan.id
    return result


@app.post(
    "/analyze/label-compliance",
    response_model=LabelComplianceReport,
    description=(
        "Inspect OCR label text for Indian packaged-food declarations. "
        "This does not determine legal compliance or verify an FSSAI license."
    ),
)
def label_compliance_endpoint(
    data: LabelComplianceInput,
    session: Session | None = Depends(get_optional_db),
):
    knowledge_records = (
        IngredientKnowledgeRepository.load_catalog(session)
        if session is not None
        else None
    )
    return analyze_label_compliance(
        data.label_text,
        product_category=data.product_category,
        knowledge_records=knowledge_records,
        label_corrections=data.label_corrections,
        corrections_confirmed=data.corrections_confirmed,
        extraction_metadata=data.extraction_metadata,
        symbol_review=data.symbol_review,
    )


@app.post("/analyze/product/question")
def product_question_endpoint(data: ProductQuestionInput):
    result = answer_product_question(
        data.question,
        data.context,
        explanation_level=data.explanation_level,
    )
    return result


@app.post("/analyze/product/ask")
def product_ask_endpoint(
    data: ProductQuestionInput,
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
):
    enforce_request_rate_limit(request, "product_ask")
    return ask_product_question(
        data.question,
        data.context,
        explanation_level=data.explanation_level,
        user_id=current_user.id if current_user is not None else None,
    )


@app.get("/scans", response_model=list[ScanRead])
def list_scan_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    return ScanRepository.list_for_user(
        session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@app.get("/scans/{scan_id}", response_model=ScanRead)
def read_scan_history_item(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    scan = ScanRepository.get_for_user(
        session,
        scan_id=scan_id,
        user_id=current_user.id,
    )
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan was not found.")
    return scan


@app.post(
    "/extract/label",
    description=(
        "Extract label text, candidate nutrition fields, and food suggestions "
        "from one local image upload. Maximum upload size is 15 MB."
    ),
)
async def extract_label_endpoint(
    request: Request,
    file: UploadFile = File(...),
    session: Session | None = Depends(get_optional_db),
):
    enforce_request_rate_limit(request, "extract_label")
    image_bytes = await file.read(MAX_IMAGE_UPLOAD_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds the 15 MB upload limit.",
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
        image_data = await run_in_threadpool(
            label_ocr.extract_image_data,
            image_bytes,
        )
        vision_result = None
        if (
            get_gemini_api_key()
            and os.environ.get("DISABLE_GEMINI_VISION", "").casefold() != "true"
        ):
            vision_result = await run_in_threadpool(
                extract_label_with_vision,
                image_bytes,
            )
    except label_ocr.UnsupportedImageFormatError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except label_ocr.ImageTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except label_ocr.InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except label_ocr.OCRServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    ocr_text = image_data["ocr_text"]
    parsed = parse_label_text(ocr_text)
    parsed.update(
        {
            "raw_ocr_text": image_data["raw_ocr_text"],
            "regions": image_data["regions"],
            "fields": image_data["fields"],
            "symbol_detection": image_data["symbol_detection"],
            "processing": image_data["processing"],
            "ocr_quality": image_data["ocr_quality"],
            "ocr_passes": image_data["ocr_passes"],
        }
    )
    parsed["compliance_report"] = analyze_label_compliance(
        ocr_text,
        extraction_metadata=image_data,
        knowledge_records=(
            IngredientKnowledgeRepository.load_catalog(session)
            if session is not None
            else None
        ),
    )
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
    if vision_result and vision_result.get("vision_provider") == "gemini":
        vision_product_name = vision_result.get("product_name")
        parsed["vision_provider"] = "gemini"
        parsed["vision_candidates"] = {
            "product_name": (
                vision_product_name.get("value")
                if isinstance(vision_product_name, dict)
                else vision_product_name
            ),
            "basis": vision_result.get("basis"),
            "serving_size_text": vision_result.get("serving_size_text"),
            "nutrients": {
                name: details.get("value")
                for name, details in (vision_result.get("nutrients") or {}).items()
                if isinstance(details, dict)
            },
            "ingredients_text": vision_result.get("ingredients_text"),
            "ingredients": vision_result.get("ingredients"),
            "model_used": vision_result.get("model_used"),
            "review_required": True,
        }
        suggestions = vision_result.get("food_suggestions")
        if isinstance(suggestions, list) and suggestions:
            parsed["food_suggestions"] = suggestions
            parsed["dietary_advice"] = vision_result.get("dietary_advice") or ""
        else:
            parsed["food_suggestions"] = []
            parsed["dietary_advice"] = ""
    else:
        parsed["vision_provider"] = (
            vision_result.get("vision_provider")
            if vision_result
            else "rule_based"
        )
        nutrient_values = {
            name: details.get("value")
            for name, details in (parsed.get("nutrients") or {}).items()
            if isinstance(details, dict)
        }
        suggestions, advice = generate_fallback_food_suggestions(
            product_name=(parsed.get("product_name") or {}).get("value"),
            nutrients=nutrient_values,
            ingredients_text=parsed.get("ingredients_text"),
        )
        parsed["food_suggestions"] = suggestions
        parsed["dietary_advice"] = advice
        parsed["vision_candidates"] = None
    return parsed
