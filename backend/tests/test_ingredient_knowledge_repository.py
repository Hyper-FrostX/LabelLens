from app.repositories.ingredient_knowledge_repository import (
    IngredientKnowledgeRepository,
)
from app.models import Ingredient
from app.services.ingredient_analysis import analyze_ingredients
from sqlalchemy import select


def test_curated_seed_is_idempotent_and_catalog_is_queryable(db_session):
    first_seed = IngredientKnowledgeRepository.seed_curated_data(db_session)
    second_seed = IngredientKnowledgeRepository.seed_curated_data(db_session)

    assert first_seed["ingredients"] > 0
    assert first_seed["identifiers"] >= 12
    assert second_seed == {
        "ingredients": 0,
        "aliases": 0,
        "identifiers": 0,
        "allergen_associations": 0,
        "evidence": 0,
        "regulatory_references": 0,
        "allergens": 0,
    }

    catalog = IngredientKnowledgeRepository.load_catalog(db_session)
    result = analyze_ingredients(
        ["E-211", "INS 621"],
        ingredients_available=True,
        knowledge_records=catalog,
    )

    assert [item["canonical_name"] for item in result["ingredients"]] == [
        "Sodium benzoate",
        "Monosodium glutamate",
    ]
    assert result["ingredients"][0]["identifiers"]
    assert all(
        not source["verified"]
        for item in result["ingredients"]
        for source in item["source_references"]
    )


def test_seeded_verification_statuses_and_verified_evidence_are_scoped(db_session):
    IngredientKnowledgeRepository.seed_curated_data(db_session)

    ingredients = {
        ingredient.canonical_name: ingredient
        for ingredient in db_session.scalars(select(Ingredient)).all()
    }
    assert ingredients["Peanut"].verification_status == "PROVISIONAL"
    assert ingredients["Rice grits"].verification_status == "UNVERIFIED"
    assert ingredients["Citric acid"].verification_status == "REVIEW_REQUIRED"
    assert ingredients["Aspartame"].verification_status == "PROVISIONAL"

    analysis = analyze_ingredients(
        ["Aspartame"],
        ingredients_available=True,
        knowledge_records=IngredientKnowledgeRepository.load_catalog(db_session),
    )
    aspartame = analysis["ingredients"][0]
    assert aspartame["verification_status"] == "PROVISIONAL"
    assert "limited evidence" in aspartame["explanation"]
    assert "risk from this product" in aspartame["explanation"]
    assert aspartame["source_references"][0]["verified"] is True
    assert aspartame["needs_review"] is True
