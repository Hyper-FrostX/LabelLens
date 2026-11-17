import pytest

from app.models import HealthProfile, User
from app.schemas.product_analysis import ProductAnalysisInput
from app.services.food_scoring import (
    ingredient_transparency_score,
    nutrition_quality_score,
    protein_quality_score,
)
from app.services.nutrition_intelligence import build_nutrition_intelligence
from app.services.personalized_suitability import evaluate_product_suitability
from app.services.product_analysis import _report_alternatives, answer_product_question


def test_normalizes_metric_serving_and_energy_units_without_crossing_bases():
    data = ProductAnalysisInput(
        basis="per_serving",
        serving_size_text="30 g",
        sugar_g=6,
        sugar_unit="g",
        sodium_mg=120,
        sodium_unit="mg",
        saturated_fat_g=1.5,
        saturated_fat_unit="g",
        additional_nutrients={
            "energy_kj": {"value": 418.4, "unit": "kJ"},
            "protein_g": {"value": 3, "unit": "g"},
        },
    )

    intelligence = build_nutrition_intelligence(data)

    assert intelligence["normalized_basis"] == "per_100g"
    assert intelligence["nutrient_density_per_100"]["sugar"]["value"] == 20
    assert intelligence["nutrient_density_per_100"]["energy"]["value"] == 333.3333
    assert intelligence["per_serving"]["protein"]["value"] == 3
    assert intelligence["ratios"]["protein_g_per_100_kcal"] == 3


def test_does_not_infer_density_from_unrecognized_units_or_missing_basis():
    data = ProductAnalysisInput(
        sugar_g=10,
        sugar_unit="cups",
        additional_nutrients={"protein_g": {"value": 5, "unit": "g"}},
    )

    intelligence = build_nutrition_intelligence(data)

    assert intelligence["nutrient_density_per_100"] == {}
    assert intelligence["normalized_basis"] is None


def test_versioned_nutrition_quality_requires_all_scored_nutrients():
    incomplete = ProductAnalysisInput(
        basis="per_100g",
        sugar_g=5,
        sugar_unit="g",
        sodium_mg=100,
        sodium_unit="mg",
    )
    incomplete_result = nutrition_quality_score(build_nutrition_intelligence(incomplete))
    assert incomplete_result["status"] == "insufficient_data"
    assert incomplete_result["score"] is None
    assert "saturated_fat" in incomplete_result["missing_inputs"]

    complete = ProductAnalysisInput(
        basis="per_100g",
        sugar_g=5,
        sugar_unit="g",
        sodium_mg=100,
        sodium_unit="mg",
        saturated_fat_g=2,
        saturated_fat_unit="g",
    )
    score = nutrition_quality_score(build_nutrition_intelligence(complete))
    assert score["version"] == "label-lens-food-scores-v1"
    assert score["score"] == 81
    assert "not a regulatory grade" in score["explanation"]


def test_protein_index_and_ingredient_transparency_report_missing_data():
    data = ProductAnalysisInput(
        basis="per_100g",
        ingredients_text="oats, honey",
        additional_nutrients={
            "energy_kcal": {"value": 200, "unit": "kcal"},
            "protein_g": {"value": 10, "unit": "g"},
        },
        allergens=["Milk"],
    )
    intelligence = build_nutrition_intelligence(data)
    protein = protein_quality_score(intelligence)
    transparency = ingredient_transparency_score(data)

    assert protein["score"] == 100
    assert protein["inputs"] == {"protein_g_per_100_kcal": 5}
    assert transparency["score"] == 80
    assert transparency["status"] == "partial_data"
    assert "safety" in transparency["explanation"]

    no_ingredients = ingredient_transparency_score(ProductAnalysisInput())
    assert no_ingredients["score"] is None
    assert no_ingredients["status"] == "insufficient_data"


def _configured_user(*, preferences=(), exclusions=(), goals=()):
    return User(
        id=1,
        name="Profile",
        email="profile@example.com",
        password_hash="unused",
        health_profile=HealthProfile(
            dietary_preferences=list(preferences),
            ingredient_exclusions=list(exclusions),
            nutrition_goals=list(goals),
        ),
    )


def test_personal_suitability_distinguishes_confirmed_preference_conflicts():
    user = _configured_user(preferences=["Vegetarian"])
    data = ProductAnalysisInput(
        symbol_review="NON_VEGETARIAN",
        corrections_confirmed=True,
    )
    result = evaluate_product_suitability(
        user=user,
        data=data,
        intelligence=build_nutrition_intelligence(data),
        legacy_profile_analysis=None,
    )

    assert result["status"] == "UNSUITABLE_BASED_ON_USER_PREFERENCES"
    assert result["profile_alignment_score"] == 0
    assert "not a safety" in result["score_meaning"]

    vegan_result = evaluate_product_suitability(
        user=_configured_user(preferences=["Vegan"]),
        data=data,
        intelligence=build_nutrition_intelligence(data),
        legacy_profile_analysis=None,
    )
    assert vegan_result["status"] == "UNSUITABLE_BASED_ON_USER_PREFERENCES"


def test_personal_suitability_keeps_unknown_ingredients_and_goals_unresolved():
    user = _configured_user(preferences=["Vegan"], exclusions=["palm oil"])
    data = ProductAnalysisInput()
    result = evaluate_product_suitability(
        user=user,
        data=data,
        intelligence=build_nutrition_intelligence(data),
        legacy_profile_analysis=None,
    )

    assert result["status"] == "NEEDS_REVIEW"
    assert result["profile_alignment_score"] is None
    assert {item["status"] for item in result["assessments"]} == {"unknown"}
    assert result["missing_inputs"]


def test_personal_suitability_marks_goal_threshold_and_exclusion_conflicts():
    user = _configured_user(exclusions=["palm oil"], goals=["lower_sugar"])
    data = ProductAnalysisInput(
        basis="per_100g",
        sugar_g=12,
        sugar_unit="g",
        ingredients_text="palm oil, sugar",
    )
    result = evaluate_product_suitability(
        user=user,
        data=data,
        intelligence=build_nutrition_intelligence(data),
        legacy_profile_analysis=None,
    )

    assert result["status"] == "POTENTIAL_CONFLICT"
    assert all(
        item["status"] == "potential_conflict"
        for item in result["assessments"]
    )


def test_daily_targets_are_reported_as_contributions_not_suitability_claims():
    user = _configured_user()
    user.health_profile.calorie_goal_kcal = 2000
    data = ProductAnalysisInput(
        basis="per_serving",
        additional_nutrients={
            "energy_kcal": {"value": 250, "unit": "kcal"},
        },
    )
    intelligence = build_nutrition_intelligence(data)
    result = evaluate_product_suitability(
        user=user,
        data=data,
        intelligence=intelligence,
        legacy_profile_analysis=None,
    )

    assert result["status"] == "NEEDS_REVIEW"
    assert result["profile_alignment_score"] is None
    assert result["goal_contributions"]["calorie_goal_kcal"][
        "percent_of_user_target_per_serving"
    ] == 12.5


def test_goal_ranked_alternatives_use_real_comparable_values_and_flag_profile():
    data = ProductAnalysisInput(
        product_name="Current bar",
        basis="per_100g",
        sugar_g=20,
        sugar_unit="g",
        sodium_mg=500,
        sodium_unit="mg",
        recommendation_goal="lower_sugar",
    )
    user = _configured_user(exclusions=["palm oil"])
    result = _report_alternatives(
        data,
        [
            {
                "product_name": "Lower sugar stored bar",
                "input": {
                    "basis": "per_100g",
                    "sugar_g": 10,
                    "sugar_unit": "g",
                    "sodium_mg": 600,
                    "sodium_unit": "mg",
                    "ingredients_text": "palm oil, oats",
                },
            },
            {
                "product_name": "Wrong basis",
                "input": {
                    "basis": "per_100ml",
                    "sugar_g": 1,
                    "sugar_unit": "g",
                    "sodium_mg": 1,
                    "sodium_unit": "mg",
                },
            },
        ],
        current_user=user,
    )

    assert result["status"] == "POTENTIAL_ALTERNATIVES"
    assert result["recommendation_goal"] == "lower_sugar"
    recommendation = result["items"][0]
    assert recommendation["product"] == "Lower sugar stored bar"
    assert recommendation["tradeoffs"][0]["nutrient"] == "sodium_mg"
    assert recommendation["profile_compatibility"] == "POTENTIAL_CONFLICT"
    assert recommendation["source_provenance"] == "user_saved_analysis"
    assert recommendation["ingredient_transparency"]["ingredient_list"] == "provided"
    assert recommendation["nutritional_values_considered"]
    assert recommendation["data_completeness"]["missing_nutrients"]


def _recommendation_input(name, *, sugar, sodium, saturated, calories, protein, fiber):
    return {
        "product_name": name,
        "basis": "per_100g",
        "sugar_g": sugar,
        "sugar_unit": "g",
        "added_sugar_g": max(sugar - 2, 0),
        "added_sugar_unit": "g",
        "sodium_mg": sodium,
        "sodium_unit": "mg",
        "saturated_fat_g": saturated,
        "saturated_fat_unit": "g",
        "additional_nutrients": {
            "energy_kcal": {"value": calories, "unit": "kcal"},
            "protein_g": {"value": protein, "unit": "g"},
            "fiber_g": {"value": fiber, "unit": "g"},
            "total_fat_g": {"value": 10, "unit": "g"},
            "carbohydrates_g": {"value": 55, "unit": "g"},
        },
        "ingredients_text": "whole grain oats",
        "allergens": ["Milk"],
    }


@pytest.mark.parametrize(
    ("goal", "candidate_values"),
    [
        ("balanced", (10, 450, 3, 380, 12, 4)),
        ("lower_sugar", (10, 550, 6, 420, 6, 2)),
        ("lower_sodium", (25, 300, 6, 420, 6, 2)),
        ("lower_saturated_fat", (25, 550, 2, 420, 6, 2)),
        ("higher_protein", (25, 550, 6, 420, 15, 2)),
        ("higher_fiber", (25, 550, 6, 420, 6, 6)),
        ("lower_calories", (25, 550, 6, 300, 6, 2)),
    ],
)
def test_recommendations_rank_real_records_for_supported_goals(goal, candidate_values):
    data = ProductAnalysisInput.model_validate(
        _recommendation_input(
            "Current bar",
            sugar=25,
            sodium=550,
            saturated=6,
            calories=420,
            protein=6,
            fiber=2,
        )
        | {"recommendation_goal": goal}
    )
    candidate = _recommendation_input(
        "Recorded candidate",
        sugar=candidate_values[0],
        sodium=candidate_values[1],
        saturated=candidate_values[2],
        calories=candidate_values[3],
        protein=candidate_values[4],
        fiber=candidate_values[5],
    )

    result = _report_alternatives(
        data,
        [
            {"product_name": "Recorded candidate", "input": candidate},
            {"product_name": "Different basis", "input": {**candidate, "basis": "per_100ml"}},
        ],
    )

    assert result["status"] == "POTENTIAL_ALTERNATIVES"
    assert result["recommendation_goal"] == goal
    assert [item["product"] for item in result["items"]] == ["Recorded candidate"]
    assert result["items"][0]["source_provenance"] == "user_saved_analysis"
    assert "no aggregate food-quality score" in result["ranking_method"].casefold()


def test_recommendations_normalize_stated_servings_and_report_incompatible_missing_data():
    current = ProductAnalysisInput(
        product_name="Serving-sized bar",
        basis="per_serving",
        serving_size_text="40 g",
        sugar_g=8,
        sugar_unit="g",
        sodium_mg=200,
        sodium_unit="mg",
        recommendation_goal="lower_sugar",
    )
    serving_candidate = {
        "product_name": "Per 100 g bar",
        "basis": "per_100g",
        "sugar_g": 15,
        "sugar_unit": "g",
        "sodium_mg": 500,
        "sodium_unit": "mg",
    }
    normalized = _report_alternatives(
        current,
        [{"product_name": "Per 100 g bar", "input": serving_candidate}],
    )
    assert normalized["comparison_basis"] == "per_100g"
    assert normalized["items"][0]["improvements"][0]["current_value"] == 20

    incompatible = _report_alternatives(
        current,
        [
            {
                "product_name": "Volume bar",
                "input": {**serving_candidate, "basis": "per_100ml"},
            }
        ],
    )
    assert incompatible["status"] == "NOT_AVAILABLE"

    missing = _report_alternatives(
        current,
        [
            {
                "product_name": "Incomplete bar",
                "input": {
                    "product_name": "Incomplete bar",
                    "basis": "per_100g",
                    "sugar_g": 10,
                    "sugar_unit": "g",
                },
            }
        ],
    )
    assert missing["status"] == "NOT_AVAILABLE"
    assert missing["items"] == []


def test_saved_profile_goal_ranks_real_alternatives_without_claiming_suitability():
    data = ProductAnalysisInput(
        product_name="Current bar",
        basis="per_100g",
        sugar_g=20,
        sugar_unit="g",
        sodium_mg=500,
        sodium_unit="mg",
    )
    user = _configured_user(preferences=["Vegetarian"], goals=["lower_sugar"])
    result = _report_alternatives(
        data,
        [
            {
                "product_name": "Stored vegetarian bar",
                "input": {
                    "basis": "per_100g",
                    "sugar_g": 10,
                    "sugar_unit": "g",
                    "sodium_mg": 500,
                    "sodium_unit": "mg",
                    "label_text": "Vegetarian",
                    "symbol_review": "VEGETARIAN",
                    "corrections_confirmed": True,
                },
            }
        ],
        current_user=user,
    )

    assert result["recommendation_goal"] == "lower_sugar"
    assert result["requested_goal"] == "balanced"
    assert result["items"][0]["profile_compatibility"] == "NEEDS_REVIEW"
    assert result["items"][0]["limitation"].startswith("This is a nutrient comparison")


def test_grounded_q_and_a_reports_deterministic_fallback_and_available_strengths():
    answer = answer_product_question(
        "What are this product's strengths?",
        {
            "food_intelligence": {
                "scores": {
                    "scores": {
                        "nutrition_quality": {
                            "score": 80,
                            "status": "available",
                        },
                        "protein_quality": {
                            "score": None,
                            "status": "insufficient_data",
                        },
                    }
                }
            }
        },
    )

    assert answer["intent"] == "product_strengths"
    assert answer["evidence"]["nutrition_quality"]["score"] == 80
    assert answer["response_mode"] == "DETERMINISTIC_FALLBACK"
    assert answer["provider_status"] == "NO_GENERATIVE_PROVIDER_CONFIGURED"


def test_grounded_q_and_a_answers_from_matching_ingredient_and_nutrition_context():
    ingredient_answer = answer_product_question(
        "What is maltodextrin?",
        {
            "ingredients": {
                "analysis": {
                    "ingredients": [
                        {
                            "original_label_text": "maltodextrin",
                            "matched_name": "Maltodextrin",
                            "verification_status": "REVIEW_REQUIRED",
                        }
                    ]
                }
            }
        },
    )
    assert ingredient_answer["intent"] == "ingredient_explanation"
    assert ingredient_answer["evidence"][0]["verification_status"] == "REVIEW_REQUIRED"

    protein_answer = answer_product_question(
        "How much protein does this label report?",
        {
            "nutrition": {"basis": "per_100g"},
            "food_intelligence": {
                "nutrition": {
                    "nutrient_density_per_100": {
                        "protein": {"value": 8, "unit": "g", "basis": "per_100g"}
                    }
                },
                "scores": {"scores": {}},
            },
        },
    )
    assert protein_answer["intent"] == "nutrition"
    assert protein_answer["evidence"]["food_intelligence"]["nutrient_density_per_100"][
        "protein"
    ]["value"] == 8
