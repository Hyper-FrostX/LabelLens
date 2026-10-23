
import math
import re
from typing import Optional

# Explicit conversion assumption:
# 1 teaspoon of sugar is approximately 4 grams.
GRAMS_PER_TEASPOON_SUGAR = 4.0

# Initial project-defined reference values.
# These are configurable design thresholds, not regulatory grades.
DAILY_REFERENCE_LIMITS = {
    "sugar_g": 50.0,
    "sodium_mg": 2000.0,
    "saturated_fat_g": 22.0,
}

# Project-configurable contribution bands. These are informational bands
# against the references above, not official nutrition grades.
EXCESS_CONTRIBUTION_BANDS = {
    "lower_max_percent": 15.0,
    "moderate_max_percent": 30.0,
}
HEALTH_SCORE_WEIGHTS = {
    "sugars": 35.0,
    "sodium": 35.0,
    "saturated_fat": 30.0,
}
HEALTH_SCORE_MINIMUM_CATEGORIES = 2
HEALTH_SCORE_FORMULA = (
    "For each assessed category, penalty = min(category weight, "
    "category weight * reported amount / project daily reference). "
    "Score = max(0, round(100 - sum(penalties))). At least two of three "
    "categories must be assessable. Total sugar is preferred; added sugar "
    "is used only when total sugar is unavailable or invalid, never both."
)
EXCESS_THRESHOLD_SOURCE = (
    "Label Lens project references in app/services/nutrition.py "
    "(50 g sugars, 2,000 mg sodium, 22 g saturated fat per day) and "
    "project contribution bands; not official medical or regulatory limits."
)
_SERVING_SIZE_PATTERN = re.compile(
    r"^\s*\d+(?:\.\d+)?\s*"
    r"(?:g|grams?|kg|ml|millilit(?:er|re)s?|l|lit(?:er|re)s?|"
    r"oz|ounces?|fl\.?\s*oz|cups?|tbsp|tsp|pieces?|packs?)"
    r"(?:\s*\([^)]*\))?\s*$",
    re.IGNORECASE,
)
_CONVERTIBLE_SERVING_SIZE_PATTERN = re.compile(
    r"^\s*(?P<amount>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>g|grams?|kg|ml|millilit(?:er|re)s?|l|lit(?:er|re)s?)\b",
    re.IGNORECASE,
)


def convert_per_serving_to_100_basis(
    value: float,
    serving_size_text: str | None,
) -> dict[str, float | str] | None:
    """Convert only when a per-serving mass or volume uses known metric units."""
    if not math.isfinite(value) or value < 0:
        raise ValueError("Nutrient values must be finite and non-negative.")
    if not serving_size_text:
        return None

    match = _CONVERTIBLE_SERVING_SIZE_PATTERN.match(serving_size_text)
    if match is None:
        return None

    amount = float(match.group("amount"))
    if amount <= 0:
        return None

    unit = match.group("unit").casefold()
    if unit == "kg":
        serving_amount = amount * 1000
        basis = "per_100g"
    elif unit in {"g", "gram", "grams"}:
        serving_amount = amount
        basis = "per_100g"
    elif unit in {"l", "liter", "liters", "litre", "litres"}:
        serving_amount = amount * 1000
        basis = "per_100ml"
    else:
        serving_amount = amount
        basis = "per_100ml"

    return {
        "value": round(value * 100 / serving_amount, 4),
        "basis": basis,
    }


def sugar_to_teaspoons(sugar_g: float) -> float:
    """Convert grams of sugar into approximate teaspoons."""
    if not math.isfinite(sugar_g):
        raise ValueError("Sugar must be finite.")

    if sugar_g < 0:
        raise ValueError("Sugar cannot be negative.")

    return round(sugar_g / GRAMS_PER_TEASPOON_SUGAR, 2)


def assess_nutrient(
    value: Optional[float],
    daily_limit: float,
) -> dict:
    """
    Assess a nutrient amount against a daily reference limit.

    Initial project-defined bands:
    - good: below 15%
    - caution: 15% through 30%
    - high: above 30%

    The percentage is meaningful only when the value and limit
    use the same unit and represent comparable quantities.
    """
    if not math.isfinite(daily_limit):
        raise ValueError("Daily reference limit must be finite.")

    if value is None:
        return {
            "value": None,
            "percentage_of_daily_limit": None,
            "level": "unknown",
        }

    if not math.isfinite(value):
        raise ValueError("Nutrient values must be finite.")

    if value < 0:
        raise ValueError("Nutrient values cannot be negative.")

    if daily_limit <= 0:
        raise ValueError("Daily reference limit must be positive.")

    percentage = (value / daily_limit) * 100

    if percentage < 15:
        level = "good"
    elif percentage <= 30:
        level = "caution"
    else:
        level = "high"

    return {
        "value": value,
        "percentage_of_daily_limit": round(percentage, 2),
        "level": level,
    }


def calculate_health_score(
    *,
    sugar_g: float | None,
    added_sugar_g: float | None,
    sodium_mg: float | None,
    saturated_fat_g: float | None,
    basis: str | None,
    units: dict[str, str | None],
    serving_size_text: str | None,
) -> dict:
    """Calculate the experimental Label Lens score from valid reported data."""
    candidates = {
        "total_sugar": (sugar_g, units.get("total_sugar"), "g"),
        "added_sugar": (added_sugar_g, units.get("added_sugar"), "g"),
        "sodium": (sodium_mg, units.get("sodium"), "mg"),
        "saturated_fat": (
            saturated_fat_g,
            units.get("saturated_fat"),
            "g",
        ),
    }
    valid_basis = basis in {"per_serving", "per_100g", "per_100ml"}
    serving_size_match = (
        re.match(r"^\s*(\d+(?:\.\d+)?)", serving_size_text)
        if serving_size_text
        else None
    )
    serving_size_valid = bool(
        serving_size_text
        and _SERVING_SIZE_PATTERN.fullmatch(serving_size_text)
        and serving_size_match
        and float(serving_size_match.group(1)) > 0
    )

    def valid_candidate(name: str) -> bool:
        value, unit, expected_unit = candidates[name]
        return (
            value is not None
            and math.isfinite(value)
            and value >= 0
            and unit == expected_unit
        )

    category_inputs: list[tuple[str, str, float, str, float]] = []
    sugar_name = (
        "total_sugar"
        if valid_candidate("total_sugar")
        else "added_sugar"
        if valid_candidate("added_sugar")
        else None
    )
    if sugar_name is not None:
        category_inputs.append(
            (
                "sugars",
                "Total sugar" if sugar_name == "total_sugar" else "Added sugar",
                candidates[sugar_name][0],
                candidates[sugar_name][1],
                DAILY_REFERENCE_LIMITS["sugar_g"],
            )
        )
    for name, label, reference_key in (
        ("sodium", "Sodium", "sodium_mg"),
        ("saturated_fat", "Saturated fat", "saturated_fat_g"),
    ):
        if valid_candidate(name):
            category_inputs.append(
                (
                    name,
                    label,
                    candidates[name][0],
                    candidates[name][1],
                    DAILY_REFERENCE_LIMITS[reference_key],
                )
            )

    unavailable_reasons = []
    if not valid_basis:
        unavailable_reasons.append(
            "The measurement basis is missing or ambiguous."
        )
    elif basis == "per_serving" and not serving_size_valid:
        unavailable_reasons.append(
            "A clear, non-zero serving size is required for per-serving data."
        )

    valid_categories = category_inputs if valid_basis and (
        basis != "per_serving" or serving_size_valid
    ) else []
    completeness = {
        "assessed": len(valid_categories),
        "total": len(HEALTH_SCORE_WEIGHTS),
        "text": f"{len(valid_categories)} of {len(HEALTH_SCORE_WEIGHTS)} nutrient categories assessed",
    }
    factors = []
    total_penalty = 0.0
    factor_basis = (
        f"per serving ({serving_size_text.strip()})"
        if basis == "per_serving" and serving_size_text
        else "per 100 g"
        if basis == "per_100g"
        else "per 100 ml"
        if basis == "per_100ml"
        else "unconfirmed basis"
    )
    for category, label, value, unit, reference in valid_categories:
        weight = HEALTH_SCORE_WEIGHTS[category]
        penalty = min(weight, weight * value / reference)
        total_penalty += penalty
        factors.append(
            {
                "category": category,
                "nutrient": label,
                "value": value,
                "unit": unit,
                "basis": basis,
                "serving_size_text": (
                    serving_size_text if basis == "per_serving" else None
                ),
                "reference_value": reference,
                "weight": weight,
                "penalty": round(penalty, 2),
                "explanation": (
                    f"{label} at {value:g} {unit} {factor_basis} uses "
                    f"{value / reference * 100:.1f}% of its configured "
                    f"project reference and contributes a capped "
                    f"{penalty:.2f}-point penalty (maximum {weight:g})."
                ),
            }
        )

    if len(valid_categories) < HEALTH_SCORE_MINIMUM_CATEGORIES:
        if not valid_categories:
            unavailable_reasons.append(
                "No nutrient category has both a usable value and unit."
            )
        else:
            unavailable_reasons.append(
                "At least two valid nutrient categories are required."
            )
        return {
            "status": "unavailable",
            "score": None,
            "data_completeness": completeness,
            "factors": factors,
            "explanation": " ".join(unavailable_reasons),
            "formula": HEALTH_SCORE_FORMULA,
        }

    return {
        "status": "available",
        "score": max(0, round(100 - total_penalty)),
        "data_completeness": completeness,
        "factors": factors,
        "explanation": (
            "The score reflects only the valid nutrient categories listed "
            "below. A higher score means lower values relative to the "
            "prototype's configured references; it is not a validated "
            "measure of overall health."
        ),
        "formula": HEALTH_SCORE_FORMULA,
    }


def analyze_nutrition(
    sugar_g: Optional[float],
    sodium_mg: Optional[float],
    saturated_fat_g: Optional[float],
    basis: str,
) -> dict:
    """
    Analyze nutrition values using their stated measurement basis.

    basis must be 'per_serving' or 'per_100g'.
    Values must all refer to the same basis.
    """
    if basis not in {"per_serving", "per_100g"}:
        raise ValueError(
            "Basis must be 'per_serving' or 'per_100g'."
        )

    nutrients = {
        "sugar": assess_nutrient(
            sugar_g, DAILY_REFERENCE_LIMITS["sugar_g"]
        ),
        "sodium": assess_nutrient(
            sodium_mg, DAILY_REFERENCE_LIMITS["sodium_mg"]
        ),
        "saturated_fat": assess_nutrient(
            saturated_fat_g,
            DAILY_REFERENCE_LIMITS["saturated_fat_g"],
        ),
    }

    percentage_context = {
        "per_serving": (
            "Percentages represent contribution to the project's daily "
            "reference from one reported serving."
        ),
        "per_100g": (
            "Percentages represent contribution to the project's daily "
            "reference from 100 g of the product."
        ),
    }[basis]

    return {
        "basis": basis,
        "percentage_context": percentage_context,
        "nutrients": nutrients,
        "sugar_teaspoons": (
            sugar_to_teaspoons(sugar_g)
            if sugar_g is not None
            else None
        ),
        "note": (
            "Thresholds and good/caution/high bands are preliminary, "
            "project-defined informational references only. They are not "
            "official nutritional, health, medical, or regulatory grades, "
            "and are not medical advice."
        ),
    }


def analyze_excess_nutrients(
    *,
    sugar_g: float | None,
    added_sugar_g: float | None,
    sodium_mg: float | None,
    saturated_fat_g: float | None,
    basis: str | None,
    units: dict[str, str | None],
    serving_size_text: str | None,
) -> list[dict]:
    """Return cautious, per-nutrient contribution assessments for a label."""
    definitions = (
        ("total_sugar", "Total sugar", sugar_g, "g", "sugar_g"),
        ("added_sugar", "Added sugar", added_sugar_g, "g", "sugar_g"),
        ("sodium", "Sodium", sodium_mg, "mg", "sodium_mg"),
        (
            "saturated_fat",
            "Saturated fat",
            saturated_fat_g,
            "g",
            "saturated_fat_g",
        ),
    )
    valid_basis = basis in {"per_serving", "per_100g", "per_100ml"}
    serving_amount_match = (
        re.match(r"^\s*(\d+(?:\.\d+)?)", serving_size_text)
        if serving_size_text
        else None
    )
    serving_size_known = bool(
        serving_size_text
        and _SERVING_SIZE_PATTERN.fullmatch(serving_size_text)
        and serving_amount_match
        and float(serving_amount_match.group(1)) > 0
    )
    assessments = []

    for nutrient, label, value, expected_unit, reference_key in definitions:
        unit = units.get(nutrient)
        reference = DAILY_REFERENCE_LIMITS[reference_key]
        assessment = {
            "nutrient": nutrient,
            "value": value,
            "unit": unit,
            "basis": basis,
            "project_reference_value": reference,
            "project_reference_unit": expected_unit,
            "threshold_explanation": (
                f"Configured project reference: {reference:g} {expected_unit} "
                f"per day. Lower contribution is below "
                f"{reference * EXCESS_CONTRIBUTION_BANDS['lower_max_percent'] / 100:g} "
                f"{expected_unit}; Moderate is "
                f"{reference * EXCESS_CONTRIBUTION_BANDS['lower_max_percent'] / 100:g} "
                f"to {reference * EXCESS_CONTRIBUTION_BANDS['moderate_max_percent'] / 100:g} "
                f"{expected_unit}; High is above "
                f"{reference * EXCESS_CONTRIBUTION_BANDS['moderate_max_percent'] / 100:g} "
                f"{expected_unit} on the reported basis."
            ),
            "status": "Unable to assess",
            "explanation": "",
            "threshold_source": EXCESS_THRESHOLD_SOURCE,
            "needs_review": True,
            "percentage_of_project_reference": None,
            "equivalent_value": None,
            "equivalent_basis": None,
        }

        if value is None:
            assessment["explanation"] = (
                f"{label} was not available as a readable label value; "
                "a missing value is not treated as zero."
            )
        elif not math.isfinite(value) or value < 0:
            raise ValueError(f"{label} must be finite and non-negative.")
        elif unit != expected_unit:
            assessment["explanation"] = (
                f"The unit for {label.lower()} is missing or unclear, so "
                "its contribution cannot be assessed."
            )
        elif not valid_basis:
            assessment["explanation"] = (
                "The measurement basis is missing or ambiguous. Confirm "
                "whether the value is per serving, per 100 g, or per 100 ml."
            )
        elif basis == "per_serving" and not serving_size_known:
            assessment["explanation"] = (
                "The serving size is missing or unclear. Confirm the amount "
                "and unit shown on the label before interpreting this value."
            )
        else:
            contribution = assess_nutrient(value, reference)
            equivalent = (
                convert_per_serving_to_100_basis(value, serving_size_text)
                if basis == "per_serving"
                else None
            )
            if equivalent is not None:
                assessment["equivalent_value"] = equivalent["value"]
                assessment["equivalent_basis"] = equivalent["basis"]
            percentage = contribution["percentage_of_daily_limit"]
            assessment["percentage_of_project_reference"] = percentage
            assessment["needs_review"] = False
            if percentage < EXCESS_CONTRIBUTION_BANDS["lower_max_percent"]:
                assessment["status"] = "Lower contribution"
                band_explanation = (
                    f"below {EXCESS_CONTRIBUTION_BANDS['lower_max_percent']:g}% "
                    "of the project's configured daily reference"
                )
            elif (
                percentage
                <= EXCESS_CONTRIBUTION_BANDS["moderate_max_percent"]
            ):
                assessment["status"] = "Moderate"
                band_explanation = (
                    f"{EXCESS_CONTRIBUTION_BANDS['lower_max_percent']:g}% to "
                    f"{EXCESS_CONTRIBUTION_BANDS['moderate_max_percent']:g}% "
                    "of the project's configured daily reference"
                )
            else:
                assessment["status"] = "High"
                band_explanation = (
                    f"more than "
                    f"{EXCESS_CONTRIBUTION_BANDS['moderate_max_percent']:g}% "
                    "of the project's configured daily reference"
                )
            readable_basis = (
                f"per serving ({serving_size_text.strip()})"
                if basis == "per_serving"
                else "per 100 g"
                if basis == "per_100g"
                else "per 100 ml"
            )
            assessment["explanation"] = (
                f"{value:g} {unit} {readable_basis} is "
                f"{percentage:g}% of the project's configured daily "
                f"reference, which is {band_explanation}. This is an "
                "informational comparison, not a health or safety judgment."
            )

        assessments.append(assessment)

    return assessments
