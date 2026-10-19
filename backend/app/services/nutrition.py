
import math
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

    return {
        "basis": basis,
        "nutrients": nutrients,
        "sugar_teaspoons": (
            sugar_to_teaspoons(sugar_g)
            if sugar_g is not None
            else None
        ),
        "note": (
            "These are preliminary project-defined thresholds. "
            "They are not official regulatory grades or medical advice."
        ),
    }
