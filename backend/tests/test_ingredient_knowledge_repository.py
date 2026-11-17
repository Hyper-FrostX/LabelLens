from sqlalchemy import select

from app.data import ingredient_knowledge
from app.data.ingredient_knowledge import get_curated_ingredient_records
from app.models import AllergenAlias, Ingredient
from app.repositories.ingredient_knowledge_repository import (
    IngredientKnowledgeRepository,
)
from app.services.ingredient_analysis import analyze_ingredients


def test_source_url_alone_does_not_verify_a_legacy_evidence_claim(monkeypatch):
    monkeypatch.setattr(
        ingredient_knowledge,
        "INGREDIENT_KNOWLEDGE_BASE",
        (
            {
                "canonical_name": "Example ingredient",
                "aliases": ("example ingredient",),
                "function": "Example function.",
                "concern_status": "evidence_based",
                "explanation": "Example claim.",
                "evidence_context": "Example limitation.",
                "evidence_source": "Unreviewed source",
                "source_url": "https://example.test/source",
            },
        ),
    )

    record = next(
        item
        for item in ingredient_knowledge.get_curated_ingredient_records()
        if item.get("canonical_name") == "Example ingredient"
    )

    assert record["verification_status"] == "REVIEW_REQUIRED"
    assert record["evidence"] == []


def test_allergen_catalog_preserves_alias_verification_status(db_session):
    allergen_records = [
        record
        for record in get_curated_ingredient_records()
        if record.get("__allergen_catalog__")
    ]

    assert len(allergen_records) == 9
    assert all(
        record["verification_status"] == "REVIEW_REQUIRED"
        for record in allergen_records
    )

    IngredientKnowledgeRepository.seed_curated_data(db_session)
    aliases = db_session.scalars(select(AllergenAlias)).all()

    assert aliases
    assert all(
        alias.verification_status == "REVIEW_REQUIRED"
        for alias in aliases
    )


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
