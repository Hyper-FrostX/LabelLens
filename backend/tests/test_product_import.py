import pytest
from pydantic import ValidationError

from app.models import Product
from app.schemas.catalog import ProductImportInput
from app.schemas.product_analysis import ProductAnalysisInput
from app.services.product_analysis import _report_alternatives
from app.services.product_import import (
    ProductImportConflict,
    import_product_record,
)


def _import_data(**overrides):
    values = {
        "product_name": "Actual source record",
        "brand": "Example brand",
        "barcode": "0123456789012",
        "category": "snack",
        "serving_size_text": "30 g",
        "ingredients_text": "oats, sugar",
        "declared_allergens": ["Wheat"],
        "may_contain": ["Peanuts"],
        "nutrients": [
            {
                "nutrient_name": "total_sugar",
                "amount": 12,
                "unit": "g",
                "basis": "per_100g",
            },
            {
                "nutrient_name": "energy",
                "amount": 160,
                "unit": "kcal",
                "basis": "per_100g",
            },
            {
                "nutrient_name": "sodium",
                "amount": 200,
                "unit": "mg",
                "basis": "per_100g",
            },
        ],
        "source_name": "Licensed Provider",
        "source_product_id": "provider-item-1",
        "source_url": "https://provider.example/products/1",
        "source_license": "CC-BY-4.0",
    }
    values.update(overrides)
    return ProductImportInput.model_validate(values)


def test_product_import_persists_source_provenance_and_label_data(db_session):
    result = import_product_record(db_session, _import_data())
    product = result.product

    assert result.status == "CREATED"
    assert product.source_name == "Licensed Provider"
    assert product.source_product_id == "provider-item-1"
    assert product.source_license == "CC-BY-4.0"
    assert product.source_url == "https://provider.example/products/1"
    assert product.serving_size_text == "30 g"
    assert product.ingredients_text == "oats, sugar"
    assert product.declared_allergens == ["Wheat"]
    assert product.may_contain == ["Peanuts"]
    assert {item.nutrient_name for item in product.nutrients} == {
        "sugar",
        "energy",
        "sodium",
    }
    recommendation = _report_alternatives(
        ProductAnalysisInput(
            product_name="Current snack",
            product_category="snack",
            basis="per_100g",
            sugar_g=20,
            sugar_unit="g",
            sodium_mg=300,
            sodium_unit="mg",
            recommendation_goal="lower_sugar",
        ),
        [product],
    )
    assert recommendation["items"][0]["product"] == "Actual source record"
    assert recommendation["items"][0]["source_provenance"]["source_license"] == "CC-BY-4.0"
    assert recommendation["items"][0]["ingredient_transparency"]["ingredient_list"] == "provided"


def test_product_import_updates_same_source_identity_without_duplicate_rows(
    db_session,
):
    first = import_product_record(db_session, _import_data())
    updated = import_product_record(
        db_session,
        _import_data(
            product_name="Updated source record",
            nutrients=[
                {
                    "nutrient_name": "total_sugar",
                    "amount": 8,
                    "unit": "g",
                    "basis": "per_100g",
                }
            ],
        ),
    )

    assert updated.status == "UPDATED"
    assert updated.product.id == first.product.id
    assert updated.product.product_name == "Updated source record"
    assert len(updated.product.nutrients) == 1
    assert float(updated.product.nutrients[0].amount) == 8
    assert db_session.query(Product).count() == 1


def test_product_import_rejects_source_or_barcode_collision(db_session):
    import_product_record(db_session, _import_data())

    with pytest.raises(ProductImportConflict, match="different source record"):
        import_product_record(
            db_session,
            _import_data(
                source_name="Another provider",
                source_product_id="other-item",
            ),
        )


def test_product_import_flags_same_name_without_reliable_identity_for_review(
    db_session,
):
    import_product_record(db_session, _import_data(barcode=None))
    with pytest.raises(ProductImportConflict, match="review before importing"):
        import_product_record(
            db_session,
            _import_data(
                barcode=None,
                source_name="Another provider",
                source_product_id="other-item",
            ),
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"barcode": "not-a-barcode"},
        {"barcode": "0123456789013"},
        {"source_license": " "},
        {
            "nutrients": [
                {
                    "nutrient_name": "sodium",
                    "amount": 20,
                    "unit": "kcal",
                    "basis": "per_100g",
                }
            ]
        },
        {
            "nutrients": [
                {
                    "nutrient_name": "mystery_compound",
                    "amount": 20,
                    "unit": "g",
                    "basis": "per_100g",
                }
            ]
        },
        {
            "nutrients": [
                {
                    "nutrient_name": "protein",
                    "amount": 5,
                    "unit": "g",
                    "basis": "per_100g",
                },
                {
                    "nutrient_name": "protein",
                    "amount": 3,
                    "unit": "g",
                    "basis": "per_100g",
                },
            ]
        },
    ],
)
def test_product_import_rejects_invalid_provenance_or_nutrition(overrides):
    with pytest.raises(ValidationError):
        _import_data(**overrides)
