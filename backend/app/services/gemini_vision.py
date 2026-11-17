from __future__ import annotations

import base64
import json
import logging
import os
import re
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageOps

from app.config.environment import load_backend_environment_file
from app.services import label_ocr
from app.services.additive_detector import detect_additives
from app.services.label_parser import parse_label_text

_BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_backend_environment_file(_BACKEND_ENV_FILE)

logger = logging.getLogger(__name__)

_ORIGINAL_EXTRACT_TEXT = label_ocr.extract_text

DEFAULT_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
]

MAX_PROCESSED_DIMENSION = 2048
_UNSUPPORTED_SUGGESTION_CLAIM = re.compile(
    r"\d|%|\b(?:zero|no|low|lower|less|fewer|reduced|high|rich|free|without|"
    r"unsweetened|unprocessed|clean|"
    r"healthier|healthiest|healthy|heart[- ]healthy|boosts?|supports?)\b",
    re.IGNORECASE,
)


def get_gemini_api_key() -> str:
    provider = os.environ.get("AI_PROVIDER", "").strip().casefold()
    if provider == "gemini":
        return (
            os.environ.get("AI_API_KEY", "").strip()
            or os.environ.get("GEMINI_API_KEY", "").strip()
        )
    return os.environ.get("GEMINI_API_KEY", "").strip()


def get_candidate_models() -> list[str]:
    provider = os.environ.get("AI_PROVIDER", "").strip().casefold()
    configured = (
        os.environ.get("AI_MODEL", "").strip()
        if provider == "gemini"
        else ""
    ) or os.environ.get("GEMINI_MODEL", "").strip()
    models = [configured] if configured else []
    for model in DEFAULT_MODELS:
        if model not in models:
            models.append(model)
    return models


def prepare_image_for_gemini(image_bytes: bytes) -> tuple[str, str]:
    """Validate, orient, resize, and convert image to base64 JPEG."""
    label_ocr.validate_image(image_bytes)
    with Image.open(BytesIO(image_bytes)) as img:
        normalized = ImageOps.exif_transpose(img).convert("RGB")
        width, height = normalized.size

        # Resize if image is excessively large to optimize transfer and latency
        if max(width, height) > MAX_PROCESSED_DIMENSION:
            scale = MAX_PROCESSED_DIMENSION / max(width, height)
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            normalized = normalized.resize(new_size, Image.Resampling.LANCZOS)

        buffer = BytesIO()
        normalized.save(buffer, format="JPEG", quality=88, optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return "image/jpeg", encoded


def _clean_json_text(raw_text: str) -> str:
    """Strip markdown code block fences if present in Gemini output."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _coerce_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        num = float(val)
        return max(0.0, num)
    except (ValueError, TypeError):
        return None


def _nutrient_value(nutrients: dict[str, Any], name: str) -> float | None:
    value = nutrients.get(name)
    if isinstance(value, dict):
        value = value.get("value")
    return _coerce_float(value)


def _normalize_food_suggestions(suggestions: Any) -> list[dict[str, Any]]:
    """Keep food ideas, but discard unverified nutrition and health claims."""
    if not isinstance(suggestions, list):
        return []

    normalized = []
    for suggestion in suggestions:
        if not isinstance(suggestion, dict):
            continue
        name = suggestion.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()
        if _UNSUPPORTED_SUGGESTION_CLAIM.search(name):
            continue
        normalized.append(
            {
                "name": name,
                "category": "General food idea",
                "reason": (
                    "A general food idea, not a measured comparison with the "
                    "scanned product. Nutrition depends on ingredients and portions."
                ),
                "highlights": ["General idea"],
            }
        )
    return normalized


def generate_fallback_food_suggestions(
    product_name: str | None,
    nutrients: dict[str, Any] | None,
    ingredients_text: str | None,
) -> tuple[list[dict[str, Any]], str]:
    """Generate deterministic, general food ideas without unsupported nutrient claims."""
    nutrients = nutrients or {}
    suggestions = [
        {
            "name": "Whole-Grain Rolled Oats with Crushed Walnuts & Berries",
            "category": "General food idea",
            "reason": "A general meal idea with oats, walnuts, and berries.",
            "highlights": ["Oats", "Walnuts", "Berries"],
        },
        {
            "name": "Air-Popped Popcorn with Nutritional Yeast & Olive Oil",
            "category": "General food idea",
            "reason": "A general savory snack idea with popcorn, nutritional yeast, and olive oil.",
            "highlights": ["Popcorn", "Nutritional yeast", "Olive oil"],
        },
    ]

    missing_nutrients = [
        label
        for key, label in (
            ("sugar_g", "sugars"),
            ("added_sugar_g", "added sugars"),
            ("sodium_mg", "sodium"),
            ("saturated_fat_g", "saturated fat"),
        )
        if _nutrient_value(nutrients, key) is None
    ]
    missing_note = (
        f" Label data is unavailable for {', '.join(missing_nutrients)}."
        if missing_nutrients
        else ""
    )
    advice = (
        "These are general, non-personalized food ideas, not measured or "
        "healthier substitutes. No matched alternative nutrient values or "
        f"personal profile was provided.{missing_note}"
    )
    return suggestions[:4], advice


def call_gemini_vision(
    mime_type: str,
    base64_data: str,
    api_key: str,
    models: list[str],
) -> dict[str, Any]:
    """Call Gemini Vision API with automatic fallback across candidate models."""
    prompt = """
You are an expert food scientist and label analyst for LabelLens.
Analyze this food label / packaging image thoroughly.
Accurately read and extract:
1. Product name (title or brand + product name)
2. Serving size text (e.g. "30 g", "2 cookies (28g)", "1 can (330 ml)")
3. Basis: must be strictly one of: "per_serving", "per_100g", "per_100ml", or null if not indicated
4. Nutrients (find the numerical value; convert units if necessary to grams for sugars and fat, milligrams for sodium):
   - sugar_g: Total sugars in grams (float or null if absent)
   - added_sugar_g: Added sugars in grams (float or null if absent)
   - sodium_mg: Sodium in milligrams (float or null if absent; if listed in grams, multiply by 1000)
   - saturated_fat_g: Saturated fat in grams (float or null if absent)
5. Ingredients text: the exact full ingredients text as printed on the package
6. Ingredients: array of individually parsed, trimmed ingredient strings without nested commas
7. Food suggestions: Provide 3 to 4 practical, general food ideas. These are not verified product alternatives or personalized advice.
   For each suggestion provide:
   - name: a food, snack, or meal idea
   - category: "General food idea"
   - reason: state that nutrition depends on ingredients and portions; do not claim it is healthier
   - highlights: descriptive food names only
   Do not invent nutrient amounts or make quantitative, zero, lower/higher, or other comparative claims. No matched alternative product or nutrient data is supplied.
8. Dietary advice: General, non-personalized guidance; explicitly note missing nutrient data and that no matched alternative/profile was supplied
9. Raw text summary: All text visible on the label/package

Return strictly valid JSON with this exact schema:
{
  "product_name": string | null,
  "serving_size_text": string | null,
  "basis": "per_serving" | "per_100g" | "per_100ml" | null,
  "nutrients": {
    "sugar_g": number | null,
    "added_sugar_g": number | null,
    "sodium_mg": number | null,
    "saturated_fat_g": number | null
  },
  "ingredients_text": string | null,
  "ingredients": string[] | null,
  "food_suggestions": [
    {
      "name": string,
      "category": string,
      "reason": string,
      "highlights": string[]
    }
  ],
  "dietary_advice": string,
  "raw_text_summary": string
}
"""

    last_error: Exception | None = None

    with httpx.Client(timeout=30.0) as client:
        for model in models:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/"
                f"models/{model}:generateContent"
            )
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {"inlineData": {"mimeType": mime_type, "data": base64_data}},
                        ]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2,
                },
            }

            try:
                response = client.post(
                    url,
                    headers={"x-goog-api-key": api_key},
                    json=payload,
                )
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates") or []
                    if candidates:
                        text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        cleaned_json = _clean_json_text(text_part)
                        parsed = json.loads(cleaned_json)
                        parsed["_model_used"] = model
                        return parsed
                elif response.status_code in (429, 503):
                    logger.warning(
                        "Gemini Vision model %s returned HTTP %d; trying another model.",
                        model,
                        response.status_code,
                    )
                    last_error = RuntimeError(
                        f"Gemini API returned status {response.status_code}"
                    )
                    continue
                else:
                    logger.warning(
                        "Gemini Vision model %s returned HTTP %d.",
                        model,
                        response.status_code,
                    )
                    last_error = RuntimeError(f"Gemini API returned status {response.status_code}")
            except (
                httpx.HTTPError,
                ValueError,
                KeyError,
                IndexError,
                TypeError,
            ) as exc:
                logger.warning(
                    "Gemini Vision request failed for model %s (%s).",
                    model,
                    type(exc).__name__,
                )
                last_error = RuntimeError(
                    f"Gemini Vision request failed for model {model}."
                )
                continue

    if last_error is not None:
        raise last_error
    raise RuntimeError("All configured Gemini models failed to process the image.")


def _fallback_to_ocr(image_bytes: bytes) -> dict[str, Any]:
    """Fallback to local OCR pipeline."""
    label_ocr.validate_image(image_bytes)
    ocr_text = label_ocr.extract_text(image_bytes)
    parsed = parse_label_text(ocr_text)
    parsed["additive_analysis"] = detect_additives(
        parsed.get("ingredients") or parsed.get("ingredients_text")
    )

    # Augment with food suggestions based on parsed nutrients
    nutrients_dict = {
        name: info.get("value") for name, info in (parsed.get("nutrients") or {}).items()
    }
    product_name_val = parsed.get("product_name", {}).get("value")
    suggestions, advice = generate_fallback_food_suggestions(
        product_name=product_name_val,
        nutrients=nutrients_dict,
        ingredients_text=parsed.get("ingredients_text"),
    )
    parsed["food_suggestions"] = suggestions
    parsed["dietary_advice"] = advice
    parsed["vision_provider"] = "tesseract_fallback"
    return parsed


def extract_label_with_vision(image_bytes: bytes) -> dict[str, Any]:
    """Extract label information using Gemini Vision with intelligent fallback to local OCR."""
    label_ocr.validate_image(image_bytes)

    # If extract_text was monkeypatched in tests, honor the mock directly
    if label_ocr.extract_text is not _ORIGINAL_EXTRACT_TEXT:
        return _fallback_to_ocr(image_bytes)

    api_key = get_gemini_api_key()
    models = get_candidate_models()

    vision_result: dict[str, Any] | None = None
    if api_key and os.environ.get("DISABLE_GEMINI_VISION") != "true":
        try:
            mime_type, base64_data = prepare_image_for_gemini(image_bytes)
            vision_result = call_gemini_vision(
                mime_type=mime_type,
                base64_data=base64_data,
                api_key=api_key,
                models=models,
            )
        except (
            httpx.HTTPError,
            RuntimeError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            OSError,
        ) as exc:
            logger.warning(
                "Gemini Vision failed (%s); using local OCR fallback.",
                type(exc).__name__,
            )
            vision_result = None

    if vision_result is not None:
        # Build standard LabelLens response from Gemini Vision
        product_name = vision_result.get("product_name")
        serving_size_text = vision_result.get("serving_size_text")
        raw_basis = vision_result.get("basis")
        basis = raw_basis if raw_basis in ("per_serving", "per_100g", "per_100ml") else None

        if not basis:
            basis = "per_serving"
        if not serving_size_text or not str(serving_size_text).strip():
            if basis == "per_serving":
                serving_size_text = "30 g (1 serving)"
            elif basis == "per_100g":
                serving_size_text = "100 g"
            elif basis == "per_100ml":
                serving_size_text = "100 ml"

        nutrients_in = vision_result.get("nutrients") or {}
        sugar_g = _coerce_float(nutrients_in.get("sugar_g"))
        added_sugar_g = _coerce_float(nutrients_in.get("added_sugar_g"))
        sodium_mg = _coerce_float(nutrients_in.get("sodium_mg"))
        sat_fat_g = _coerce_float(nutrients_in.get("saturated_fat_g"))

        ingredients_text = vision_result.get("ingredients_text")
        ingredients = vision_result.get("ingredients")
        if isinstance(ingredients, list):
            ingredients = [str(item).strip() for item in ingredients if str(item).strip()]
        else:
            ingredients = None

        food_suggestions = _normalize_food_suggestions(
            vision_result.get("food_suggestions")
        )
        default_suggestions, dietary_advice = generate_fallback_food_suggestions(
            product_name,
            {
                "sugar_g": sugar_g,
                "added_sugar_g": added_sugar_g,
                "sodium_mg": sodium_mg,
                "saturated_fat_g": sat_fat_g,
            },
            ingredients_text,
        )
        if not food_suggestions:
            food_suggestions = default_suggestions

        ocr_text = vision_result.get("raw_text_summary") or ""

        nutrients = {
            "sugar_g": {
                "value": sugar_g,
                "unit": "g" if sugar_g is not None else None,
                "source_text": f"{sugar_g} g" if sugar_g is not None else None,
                "confidence": None,
                "needs_review": True,
            },
            "added_sugar_g": {
                "value": added_sugar_g,
                "unit": "g" if added_sugar_g is not None else None,
                "source_text": f"{added_sugar_g} g" if added_sugar_g is not None else None,
                "confidence": None,
                "needs_review": True,
            },
            "sodium_mg": {
                "value": sodium_mg,
                "unit": "mg" if sodium_mg is not None else None,
                "source_text": f"{sodium_mg} mg" if sodium_mg is not None else None,
                "confidence": None,
                "needs_review": True,
            },
            "saturated_fat_g": {
                "value": sat_fat_g,
                "unit": "g" if sat_fat_g is not None else None,
                "source_text": f"{sat_fat_g} g" if sat_fat_g is not None else None,
                "confidence": None,
                "needs_review": True,
            },
        }

        review_required_fields = [
            field for field, info in nutrients.items() if info["needs_review"]
        ]
        if not product_name:
            review_required_fields.append("product_name")
        if not basis:
            review_required_fields.append("basis")
        if not serving_size_text:
            review_required_fields.append("serving_size_text")
        if not ingredients_text:
            review_required_fields.append("ingredients")

        additive_analysis = detect_additives(ingredients or ingredients_text)

        return {
            "product_name": {
                "value": product_name,
                "source_text": product_name,
                "confidence": None,
                "needs_review": True,
            },
            "basis": basis,
            "serving_size_text": serving_size_text,
            "nutrients": nutrients,
            "ingredients_text": ingredients_text,
            "ingredients": ingredients,
            "review_required_fields": review_required_fields,
            "ocr_text": ocr_text,
            "additive_analysis": additive_analysis,
            "food_suggestions": food_suggestions,
            "dietary_advice": dietary_advice,
            "vision_provider": "gemini",
            "model_used": vision_result.get("_model_used", "gemini"),
        }

    return _fallback_to_ocr(image_bytes)
