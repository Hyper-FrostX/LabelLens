import math

import pytest

from app.services.nutrition import (
    analyze_nutrition,
    assess_nutrient,
    sugar_to_teaspoons,
)


def test_assess_nutrient_normal_value():
    assert assess_nutrient(5, 50) == {
        "value": 5,
        "percentage_of_daily_limit": 10.0,
        "level": "good",
    }


@pytest.mark.parametrize(
    ("value", "expected_level"),
    [
        (7.49, "good"),
        (7.5, "caution"),
        (15, "caution"),
        (15.01, "high"),
    ],
)
def test_assess_nutrient_threshold_boundaries(value, expected_level):
    assert assess_nutrient(value, 50)["level"] == expected_level


def test_analyze_nutrition_preserves_missing_values():
    result = analyze_nutrition(None, None, None, "per_serving")

    assert result["sugar_teaspoons"] is None
    assert result["percentage_context"] == (
        "Percentages represent contribution to the project's daily "
        "reference from one reported serving."
    )
    assert all(
        nutrient == {
            "value": None,
            "percentage_of_daily_limit": None,
            "level": "unknown",
        }
        for nutrient in result["nutrients"].values()
    )


@pytest.mark.parametrize(
    ("basis", "expected_context"),
    [
        (
            "per_serving",
            "Percentages represent contribution to the project's daily "
            "reference from one reported serving.",
        ),
        (
            "per_100g",
            "Percentages represent contribution to the project's daily "
            "reference from 100 g of the product.",
        ),
    ],
)
def test_analyze_nutrition_describes_percentage_basis(basis, expected_context):
    result = analyze_nutrition(10, 500, 2, basis)

    assert result["basis"] == basis
    assert result["percentage_context"] == expected_context
    assert result["nutrients"]["sugar"]["percentage_of_daily_limit"] == 20
    assert "not official nutritional, health, medical, or regulatory grades" in (
        result["note"]
    )


@pytest.mark.parametrize(
    ("operation", "args"),
    [
        (assess_nutrient, (-0.01, 50)),
        (sugar_to_teaspoons, (-0.01,)),
    ],
)
def test_nutrition_functions_reject_negative_values(operation, args):
    with pytest.raises(ValueError, match="cannot be negative"):
        operation(*args)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_assess_nutrient_rejects_non_finite_values(value):
    with pytest.raises(ValueError, match="finite"):
        assess_nutrient(value, 50)


@pytest.mark.parametrize("daily_limit", [math.nan, math.inf, -math.inf])
def test_assess_nutrient_rejects_non_finite_limits(daily_limit):
    with pytest.raises(ValueError, match="finite"):
        assess_nutrient(1, daily_limit)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_sugar_conversion_rejects_non_finite_values(value):
    with pytest.raises(ValueError, match="finite"):
        sugar_to_teaspoons(value)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_analyze_nutrition_rejects_non_finite_nutrients(value):
    with pytest.raises(ValueError, match="finite"):
        analyze_nutrition(value, None, None, "per_serving")
