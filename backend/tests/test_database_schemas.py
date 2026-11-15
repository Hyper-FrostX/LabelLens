import pytest
from pydantic import ValidationError

from app.models import NutrientBasis
from app.schemas import (
    AnalysisReportCreate,
    ProductCreate,
    UserAllergenCreate,
)


def test_product_schema_accepts_nested_label_facts():
    product = ProductCreate(
        product_name="Oat Crunch",
        ingredients=[
            {
                "ingredient_id": 1,
                "ingredient_order": 0,
                "original_label_text": "whole oats",
            }
        ],
        nutrients=[
            {
                "nutrient_name": "sodium",
                "amount": "120.5",
                "unit": "mg",
                "basis": "per_100g",
            }
        ],
    )

    assert product.ingredients[0].ingredient_order == 0
    assert product.nutrients[0].basis is NutrientBasis.PER_100G


def test_custom_allergen_schema_requires_a_catalog_or_custom_value():
    with pytest.raises(ValidationError):
        UserAllergenCreate()

    assert UserAllergenCreate(custom_allergen_name="Mustard").custom_allergen_name == (
        "Mustard"
    )
    assert UserAllergenCreate(allergen_id=3).allergen_id == 3


def test_analysis_report_schema_rejects_scores_outside_supported_range():
    with pytest.raises(ValidationError):
        AnalysisReportCreate(
            health_score=101,
            analysis_data={},
            scoring_version="score-v1",
        )
