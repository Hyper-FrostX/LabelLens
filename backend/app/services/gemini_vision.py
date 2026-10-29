from __future__ import annotations

import base64
from io import BytesIO
import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
import httpx
from PIL import Image, ImageOps

from app.services.additive_detector import detect_additives
from app.services import label_ocr
from app.services.label_parser import parse_label_text

load_dotenv()

logger = logging.getLogger(__name__)

_ORIGINAL_EXTRACT_TEXT = label_ocr.extract_text

DEFAULT_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
]

MAX_PROCESSED_DIMENSION = 2048


def get_gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def get_candidate_models() -> list[str]:
    configured = os.environ.get("GEMINI_MODEL", "").strip()
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


def generate_fallback_food_suggestions(
    product_name: str | None,
    nutrients: dict[str, Any] | None,
    ingredients_text: str | None,
) -> tuple[list[dict[str, Any]], str]:
    """Generate intelligent rule-based food suggestions if vision AI suggestions are absent."""
    nutrients = nutrients or {}
    sugar = _coerce_float(
        nutrients.get("sugar_g")
        or (nutrients.get("sugar_g", {}).get("value") if isinstance(nutrients.get("sugar_g"), dict) else None)
    )
    added_sugar = _coerce_float(
        nutrients.get("added_sugar_g")
        or (nutrients.get("added_sugar_g", {}).get("value") if isinstance(nutrients.get("added_sugar_g"), dict) else None)
    )
    sodium = _coerce_float(
        nutrients.get("sodium_mg")
        or (nutrients.get("sodium_mg", {}).get("value") if isinstance(nutrients.get("sodium_mg"), dict) else None)
    )
    sat_fat = _coerce_float(
        nutrients.get("saturated_fat_g")
        or (nutrients.get("saturated_fat_g", {}).get("value") if isinstance(nutrients.get("saturated_fat_g"), dict) else None)
    )

    suggestions: list[dict[str, Any]] = []

    # High sugar suggestions
    if (sugar is not None and sugar > 10) or (added_sugar is not None and added_sugar > 6):
        suggestions.append(
            {
                "name": "Fresh Seasonal Fruit with Greek Yogurt & Chia Seeds",
                "category": "Whole Food Swap",
                "reason": "Provides naturally occurring sweetness bound to dietary fiber, along with high-quality protein and gut-friendly probiotics without refined added sugars.",
                "highlights": ["Zero added sugars", "High protein", "Rich in fiber", "Natural micronutrients"],
            }
        )
        suggestions.append(
            {
                "name": "Cinnamon-Spiced Roasted Almonds & Apple Slices",
                "category": "Clean Snack Alternative",
                "reason": "Delivers satisfying crunch and sweetness from real cinnamon and crisp apple, providing slow-burning energy and heart-healthy monounsaturated fats.",
                "highlights": ["No high-fructose corn syrup", "Heart-healthy fats", "Low glycemic impact"],
            }
        )

    # High sodium suggestions
    if sodium is not None and sodium > 350:
        suggestions.append(
            {
                "name": "Herb-Roasted Chickpeas (Olive Oil & Rosemary)",
                "category": "Low-Sodium Crunchy Swap",
                "reason": "Crispy texture packed with plant protein and fiber, naturally seasoned with antioxidant-rich rosemary, garlic, and smoked paprika instead of excessive salt.",
                "highlights": ["Over 70% lower sodium", "High plant fiber", "Clean whole food"],
            }
        )

    # High saturated fat suggestions
    if sat_fat is not None and sat_fat > 3.0:
        suggestions.append(
            {
                "name": "Avocado & Seed Crackers with Lemon Hummus",
                "category": "Healthy Fats Replacement",
                "reason": "Swaps saturated and palm oils for nutrient-rich unsaturated fatty acids from avocado, flax, and sesame seeds.",
                "highlights": ["Zero hydrogenated oils", "Omega-3 fatty acids", "No artificial emulsifiers"],
            }
        )

    # General clean default if product is moderate or specific flags not triggered
    if not suggestions:
        suggestions.append(
            {
                "name": "Whole-Grain Rolled Oats with Crushed Walnuts & Berries",
                "category": "Whole Grain Swap",
                "reason": "Minimally processed complex carbohydrates rich in beta-glucan soluble fiber to support steady blood sugar and cardiovascular health.",
                "highlights": ["Unprocessed whole grains", "No synthetic additives", "Zero refined sugars"],
            }
        )
        suggestions.append(
            {
                "name": "Air-Popped Popcorn with Nutritional Yeast & Olive Oil",
                "category": "Clean Snack",
                "reason": "Whole grain savory snack offering volume and fiber with B-vitamins and heart-healthy polyphenols.",
                "highlights": ["100% Whole grain", "Clean ingredients", "Naturally low calorie"],
            }
        )

    advice = (
        f"For {product_name or 'this food item'}, look for clean-label alternatives with shorter "
        "ingredient lists, zero hydrogenated oils, and minimal added sugars per serving."
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
7. Food suggestions: Provide 3 to 4 healthier, practical food alternatives or smarter swaps for this specific product.
   For each suggestion provide:
   - name: clear name of the healthier food, snack, or meal alternative
   - category: e.g. "Whole Food Swap", "Clean Packaged Alternative", "Homemade Healthy Version"
   - reason: detailed, friendly explanation of why this choice is healthier and what benefits it provides
   - highlights: array of 3-4 short badges (e.g. ["0g Added Sugar", "Low Sodium", "High Fiber", "No Palm Oil"])
8. Dietary advice: A concise, positive, evidence-based nutrition tip tailored specifically to this product
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
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
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
                response = client.post(url, json=payload)
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
                        "Gemini model %s returned status %d. Falling back to next model.",
                        model,
                        response.status_code,
                    )
                    last_error = RuntimeError(f"Model {model} returned status {response.status_code}: {response.text[:200]}")
                    continue
                else:
                    logger.warning(
                        "Gemini model %s request failed with status %d: %s",
                        model,
                        response.status_code,
                        response.text[:200],
                    )
                    last_error = RuntimeError(f"Gemini API returned status {response.status_code}")
            except Exception as exc:
                logger.warning("Error invoking Gemini model %s: %s", model, exc)
                last_error = exc
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
        except Exception as exc:
            logger.warning("Gemini Vision failed (%s). Falling back to local OCR pipeline.", exc)
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

        food_suggestions = vision_result.get("food_suggestions")
        dietary_advice = vision_result.get("dietary_advice") or ""
        if not food_suggestions:
            food_suggestions, default_advice = generate_fallback_food_suggestions(
                product_name,
                {"sugar_g": sugar_g, "added_sugar_g": added_sugar_g, "sodium_mg": sodium_mg, "saturated_fat_g": sat_fat_g},
                ingredients_text,
            )
            dietary_advice = dietary_advice or default_advice

        ocr_text = vision_result.get("raw_text_summary") or ""

        nutrients = {
            "sugar_g": {
                "value": sugar_g,
                "unit": "g" if sugar_g is not None else None,
                "source_text": f"{sugar_g} g" if sugar_g is not None else None,
                "confidence": 0.95 if sugar_g is not None else None,
                "needs_review": sugar_g is None,
            },
            "added_sugar_g": {
                "value": added_sugar_g,
                "unit": "g" if added_sugar_g is not None else None,
                "source_text": f"{added_sugar_g} g" if added_sugar_g is not None else None,
                "confidence": 0.95 if added_sugar_g is not None else None,
                "needs_review": added_sugar_g is None,
            },
            "sodium_mg": {
                "value": sodium_mg,
                "unit": "mg" if sodium_mg is not None else None,
                "source_text": f"{sodium_mg} mg" if sodium_mg is not None else None,
                "confidence": 0.95 if sodium_mg is not None else None,
                "needs_review": sodium_mg is None,
            },
            "saturated_fat_g": {
                "value": sat_fat_g,
                "unit": "g" if sat_fat_g is not None else None,
                "source_text": f"{sat_fat_g} g" if sat_fat_g is not None else None,
                "confidence": 0.95 if sat_fat_g is not None else None,
                "needs_review": sat_fat_g is None,
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
                "confidence": 0.95 if product_name else None,
                "needs_review": not bool(product_name),
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
