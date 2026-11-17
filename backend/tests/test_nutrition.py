import math

import pytest

from app.services.nutrition import (
    DAILY_REFERENCE_LIMITS,
    EXCESS_CONTRIBUTION_BANDS,
    analyze_excess_nutrients,
    analyze_nutrition,
    assess_nutrient,
    calculate_health_score,
    convert_per_serving_to_100_basis,
    sugar_to_teaspoons,
)


def _excess_assessments(
    *,
    sugar=10,
    added_sugar=3,
    sodium=400,
    saturated_fat=5,
    basis="per_serving",
    serving_size="30 g",
    units=None,
):
    return analyze_excess_nutrients(
        sugar_g=sugar,
        added_sugar_g=added_sugar,
        sodium_mg=sodium,
        saturated_fat_g=saturated_fat,
        basis=basis,
        units=units
        if units is not None
        else {
            "total_sugar": "g",
            "added_sugar": "g",
            "sodium": "mg",
            "saturated_fat": "g",
        },
        serving_size_text=serving_size,
    )


def test_excess_nutrients_return_values_units_basis_and_plain_explanations():
    results = _excess_assessments()

    assert [item["nutrient"] for item in results] == [
        "total_sugar",
        "added_sugar",
        "sodium",
        "saturated_fat",
    ]
    assert results[0]["value"] == 10
    assert results[0]["unit"] == "g"
    assert results[0]["basis"] == "per_serving"
    assert results[0]["status"] == "Moderate"
    assert "10 g per serving (30 g)" in results[0]["explanation"]
    assert results[0]["needs_review"] is False
    assert results[0]["threshold_source"]
    assert results[0]["project_reference_value"] == 50
    assert results[0]["project_reference_unit"] == "g"
    assert "High is above 15 g" in results[0]["threshold_explanation"]
    assert results[0]["value"] != results[1]["value"]


@pytest.mark.parametrize(
    ("value", "expected_status"),
    [
        (7.49, "Lower contribution"),
        (7.5, "Moderate"),
        (15, "Moderate"),
        (15.01, "High"),
    ],
)
def test_excess_nutrient_status_boundaries(value, expected_status):
    results = _excess_assessments(
        sugar=value,
        added_sugar=None,
        sodium=None,
        saturated_fat=None,
        basis="per_100g",
        serving_size=None,
    )

    assert results[0]["status"] == expected_status
    assert results[0]["needs_review"] is False
    assert results[0]["percentage_of_project_reference"] == pytest.approx(
        value / DAILY_REFERENCE_LIMITS["sugar_g"] * 100
    )


def test_excess_nutrient_thresholds_are_configurable(monkeypatch):
    monkeypatch.setitem(DAILY_REFERENCE_LIMITS, "sugar_g", 100)
    monkeypatch.setitem(EXCESS_CONTRIBUTION_BANDS, "lower_max_percent", 5)

    result = _excess_assessments(
        sugar=10,
        added_sugar=None,
        sodium=None,
        saturated_fat=None,
        basis="per_100g",
        serving_size=None,
    )[0]

    assert result["percentage_of_project_reference"] == 10
    assert result["status"] == "Moderate"
    assert "High is above 30 g" in result["threshold_explanation"]


@pytest.mark.parametrize(
    ("serving_size", "expected_basis", "expected_value"),
    [
        ("30 g", "per_100g", 33.3333),
        ("0.5 kg", "per_100g", 2.0),
        ("250 ml", "per_100ml", 4.0),
        ("1 l", "per_100ml", 1.0),
    ],
)
def test_per_serving_conversion_requires_known_metric_mass_or_volume(
    serving_size, expected_basis, expected_value
):
    converted = convert_per_serving_to_100_basis(10, serving_size)

    assert converted == {
        "value": expected_value,
        "basis": expected_basis,
    }


@pytest.mark.parametrize("serving_size", [None, "", "1 cup", "30 oz", "0 g"])
def test_per_serving_conversion_skips_unknown_or_unsupported_units(serving_size):
    assert convert_per_serving_to_100_basis(10, serving_size) is None


def test_per_serving_conversion_is_returned_without_replacing_label_value():
    result = _excess_assessments(
        sugar=10,
        added_sugar=None,
        sodium=None,
        saturated_fat=None,
        basis="per_serving",
        serving_size="30 g",
    )[0]

    assert result["value"] == 10
    assert result["basis"] == "per_serving"
    assert result["equivalent_value"] == 33.3333
    assert result["equivalent_basis"] == "per_100g"


def _health_score(
    *,
    sugar=10,
    added_sugar=5,
    sodium=1000,
    saturated_fat=11,
    basis="per_100g",
    serving_size=None,
    units=None,
):
    return calculate_health_score(
        sugar_g=sugar,
        added_sugar_g=added_sugar,
        sodium_mg=sodium,
        saturated_fat_g=saturated_fat,
        basis=basis,
        units=units
        if units is not None
        else {
            "total_sugar": "g",
            "added_sugar": "g",
            "sodium": "mg",
            "saturated_fat": "g",
        },
        serving_size_text=serving_size,
    )


def test_health_score_uses_documented_weighted_formula():
    score = _health_score()

    assert score["status"] == "available"
    assert score["score"] == 60
    assert score["data_completeness"] == {
        "assessed": 3,
        "total": 3,
        "text": "3 of 3 nutrient categories assessed",
    }
    assert [factor["category"] for factor in score["factors"]] == [
        "sugars",
        "sodium",
        "saturated_fat",
    ]
    assert [factor["penalty"] for factor in score["factors"]] == [
        7.0,
        17.5,
        15.0,
    ]
    assert all(factor["basis"] == "per_100g" for factor in score["factors"])
    assert "At least two of three categories" in score["formula"]


def test_health_score_never_double_penalizes_total_and_added_sugar():
    score = _health_score(sugar=20, added_sugar=50, sodium=None, saturated_fat=None)

    assert score["status"] == "unavailable"
    assert score["data_completeness"]["assessed"] == 1
    assert [factor["nutrient"] for factor in score["factors"]] == [
        "Total sugar"
    ]
    assert "At least two valid nutrient categories" in score["explanation"]


def test_health_score_uses_added_sugar_when_total_sugar_is_missing():
    score = _health_score(sugar=None, added_sugar=10, sodium=1000, saturated_fat=None)

    assert score["status"] == "available"
    assert score["data_completeness"]["text"] == (
        "2 of 3 nutrient categories assessed"
    )
    assert [factor["nutrient"] for factor in score["factors"]] == [
        "Added sugar",
        "Sodium",
    ]


def test_health_score_uses_per_serving_values_only_with_known_serving_size():
    score = _health_score(
        sugar=10,
        added_sugar=None,
        sodium=1000,
        saturated_fat=None,
        basis="per_serving",
        serving_size="30 g",
    )

    assert score["status"] == "available"
    assert score["data_completeness"]["assessed"] == 2
    assert all(
        factor["serving_size_text"] == "30 g"
        and "per serving (30 g)" in factor["explanation"]
        for factor in score["factors"]
    )


def test_health_score_caps_penalties_at_category_weights():
    score = _health_score(
        sugar=100,
        added_sugar=100,
        sodium=5000,
        saturated_fat=44,
    )

    assert score["score"] == 0
    assert [factor["penalty"] for factor in score["factors"]] == [
        35,
        35,
        30,
    ]


def test_health_score_zero_values_are_valid_and_score_as_zero_penalty():
    score = _health_score(sugar=0, added_sugar=0, sodium=0, saturated_fat=0)

    assert score["status"] == "available"
    assert score["score"] == 100
    assert all(factor["penalty"] == 0 for factor in score["factors"])


@pytest.mark.parametrize(
    ("basis", "serving_size", "units", "sugar", "sodium"),
    [
        ("unknown", None, None, 10, 100),
        ("per_serving", None, None, 10, 100),
        (
            "per_100g",
            None,
            {"total_sugar": "mg", "sodium": "mg"},
            10,
            100,
        ),
        ("per_100g", None, None, None, None),
    ],
)
def test_health_score_unavailable_for_insufficient_or_ambiguous_data(
    basis, serving_size, units, sugar, sodium
):
    score = _health_score(
        sugar=sugar,
        added_sugar=None,
        sodium=sodium,
        saturated_fat=None,
        basis=basis,
        serving_size=serving_size,
        units=units,
    )

    assert score["status"] == "unavailable"
    assert score["score"] is None
    assert score["explanation"]


@pytest.mark.parametrize(
    ("basis", "serving_size", "expected_basis"),
    [
        ("per_100g", None, "per_100g"),
        ("per_100ml", None, "per_100ml"),
        ("per_serving", "250 ml", "per_serving"),
    ],
)
def test_excess_nutrients_preserve_valid_measurement_basis(
    basis, serving_size, expected_basis
):
    results = _excess_assessments(
        basis=basis,
        serving_size=serving_size,
        sugar=10,
        added_sugar=None,
        sodium=None,
        saturated_fat=None,
    )

    assert results[0]["basis"] == expected_basis
    assert results[0]["status"] != "Unable to assess"


def test_excess_nutrients_mark_missing_values_as_unknown_not_zero():
    results = _excess_assessments(
        sugar=None,
        added_sugar=None,
        sodium=None,
        saturated_fat=None,
    )

    assert all(item["value"] is None for item in results)
    assert all(item["status"] == "Unable to assess" for item in results)
    assert all(item["needs_review"] for item in results)
    assert "not treated as zero" in results[0]["explanation"]


@pytest.mark.parametrize(
    ("basis", "serving_size", "units"),
    [
        ("unclear", "30 g", {"total_sugar": "g"}),
        ("per_serving", None, {"total_sugar": "g"}),
        ("per_100g", None, {"total_sugar": "mg"}),
        ("per_100ml", None, {}),
    ],
)
def test_excess_nutrients_require_unambiguous_basis_unit_and_serving(
    basis, serving_size, units
):
    results = _excess_assessments(
        sugar=10,
        added_sugar=None,
        sodium=None,
        saturated_fat=None,
        basis=basis,
        serving_size=serving_size,
        units=units,
    )

    assert results[0]["status"] == "Unable to assess"
    assert results[0]["needs_review"] is True


@pytest.mark.parametrize("value", [-1, math.nan, math.inf])
def test_excess_nutrients_reject_invalid_values(value):
    with pytest.raises(ValueError):
        _excess_assessments(
            sugar=value,
            added_sugar=None,
            sodium=None,
            saturated_fat=None,
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
        (
            "per_100ml",
            "Percentages represent contribution to the project's daily "
            "reference from 100 ml of the product.",
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
