import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.config import get_db
from app.repositories.ingredient_knowledge_repository import (
    IngredientKnowledgeRepository,
)
from main import app


@pytest.fixture
def personalized_client(db_engine, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", secrets.token_urlsafe(48))

    def override_get_db():
        with Session(db_engine, expire_on_commit=False) as session:
            yield session

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    if previous_override is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous_override


def _create_profile(
    client: TestClient,
    *,
    email: str = "person@example.com",
    conditions: list[str] | None = None,
    allergens: list[str] | None = None,
    custom_allergens: list[str] | None = None,
) -> dict[str, str]:
    password = "StrongPass123!"
    registered = client.post(
        "/auth/register",
        json={"name": "Test Person", "email": email, "password": password},
    )
    assert registered.status_code == 201
    token_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert token_response.status_code == 200
    headers = {
        "Authorization": f"Bearer {token_response.json()['access_token']}"
    }
    profile_update = client.put(
        "/profile",
        headers=headers,
        json={
            "name": "Test Person",
            "expertise_level": "beginner",
            "health_conditions": conditions or [],
            "allergens": allergens or [],
            "custom_allergens": custom_allergens or [],
        },
    )
    assert profile_update.status_code == 200
    return headers


@pytest.mark.parametrize(
    ("allergen", "ingredient"),
    [
        ("Gluten", "wheat flour"),
        ("Dairy", "milk solids"),
        ("Soy", "soya oil"),
        ("Tree nuts", "almond flour"),
        ("Peanuts", "groundnuts"),
        ("Eggs", "egg white"),
        ("Fish", "salmon"),
        ("Shellfish", "shrimp"),
        ("Sesame", "tahini"),
    ],
)
def test_each_standard_allergen_matches_ingredient_text(
    personalized_client,
    allergen,
    ingredient,
):
    headers = _create_profile(personalized_client, allergens=[allergen])

    response = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json={"ingredients_text": ingredient},
    )

    assert response.status_code == 200
    findings = response.json()["personal_suitability"]["allergen_assessment"][
        "findings"
    ]
    assert len(findings) == 1
    assert findings[0]["allergen"] == allergen
    assert findings[0]["detection_source"] == "ingredient"
    assert findings[0]["severity"] == "detected_concern"
    assert findings[0]["matched_text"] == ingredient


def test_allergen_matching_uses_nested_ingredient_expansion_and_declared_text(
    personalized_client,
):
    headers = _create_profile(
        personalized_client,
        allergens=["Soy", "Dairy", "Peanuts"],
    )

    response = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json={
            "ingredients_text": "Seasoning (soy lecithin, salt)",
            "allergens": {"value": ["milk"]},
            "may_contain": {
                "value": ["peanuts"],
                "source_text": "May contain: peanuts",
            },
        },
    )

    assert response.status_code == 200
    findings = response.json()["personal_suitability"]["allergen_assessment"][
        "findings"
    ]
    assert {(item["allergen"], item["detection_source"]) for item in findings} == {
        ("Soy", "ingredient"),
        ("Dairy", "declared_allergen"),
        ("Peanuts", "may_contain_statement"),
    }
    may_contain = next(
        item for item in findings if item["detection_source"] == "may_contain_statement"
    )
    assert may_contain["severity"] == "warning"


def test_custom_allergen_uses_literal_phrase_not_fuzzy_matching(personalized_client):
    headers = _create_profile(
        personalized_client,
        custom_allergens=["Mustard"],
    )

    matched = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json={"ingredients_text": "mustard seed"},
    )
    non_match = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json={"ingredients_text": "custard powder"},
    )

    assert matched.json()["personal_suitability"]["allergen_assessment"][
        "findings"
    ][0]["allergen"] == "Mustard"
    assert non_match.json()["personal_suitability"]["allergen_assessment"][
        "findings"
    ] == []


def test_personalized_analysis_reuses_persisted_ingredient_catalog(
    personalized_client,
    db_engine,
):
    with Session(db_engine) as session:
        IngredientKnowledgeRepository.seed_curated_data(session)

    headers = _create_profile(personalized_client, allergens=["Peanuts"])
    response = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json={"ingredients_text": "E-211, groundnuts"},
    )

    assert response.status_code == 200
    result = response.json()
    assert [
        item["canonical_name"]
        for item in result["general_analysis"]["ingredient_analysis"]["ingredients"]
    ] == ["Sodium benzoate", "Peanut"]
    finding = result["personal_suitability"]["allergen_assessment"]["findings"][0]
    assert finding["allergen"] == "Peanuts"
    assert finding["detection_source"] == "ingredient"


def test_exclusion_wording_is_not_reported_as_an_allergen_match(personalized_client):
    headers = _create_profile(
        personalized_client,
        allergens=["Dairy", "Peanuts"],
    )

    response = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json={
            "ingredients_text": "non-dairy creamer, peanut-free flavoring",
            "allergens": ["free from milk"],
        },
    )

    assert response.status_code == 200
    assert response.json()["personal_suitability"]["allergen_assessment"][
        "findings"
    ] == []


def test_missing_ingredient_and_allergen_text_remains_unknown(personalized_client):
    headers = _create_profile(personalized_client, allergens=["Peanuts"])

    response = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json={"basis": "per_100g"},
    )

    suitability = response.json()["personal_suitability"]
    assert suitability["status"] == "unknown"
    assert suitability["allergen_assessment"]["status"] == "unknown"
    assert suitability["allergen_assessment"]["findings"] == []
    assert suitability["missing_information"]


@pytest.mark.parametrize(
    ("condition", "label", "expected_finding_type"),
    [
        (
            "Diabetes",
            {
                "sugar_g": 20,
                "added_sugar_g": 10,
                "sugar_unit": "g",
                "added_sugar_unit": "g",
                "basis": "per_serving",
                "serving_size_text": "30 g",
            },
            "nutrient_reference_signal",
        ),
        (
            "Hypertension",
            {
                "sodium_mg": 800,
                "sodium_unit": "mg",
                "basis": "per_serving",
                "serving_size_text": "30 g",
            },
            "nutrient_reference_signal",
        ),
        (
            "Heart disease",
            {
                "sodium_mg": 800,
                "saturated_fat_g": 8,
                "sodium_unit": "mg",
                "saturated_fat_unit": "g",
                "basis": "per_serving",
                "serving_size_text": "30 g",
            },
            "nutrient_reference_signal",
        ),
        (
            "Kidney disease",
            {
                "sodium_mg": 800,
                "sodium_unit": "mg",
                "basis": "per_serving",
                "serving_size_text": "30 g",
            },
            "nutrient_reference_signal",
        ),
        (
            "Celiac disease",
            {"ingredients_text": "wheat flour, sugar"},
            "gluten_label_evidence",
        ),
        (
            "PKU",
            {"ingredients_text": "sugar, aspartame"},
            "phenylalanine_related_label_evidence",
        ),
        ("IBS", {"ingredients_text": "oats"}, None),
        ("Gout", {"ingredients_text": "oats"}, None),
    ],
)
def test_supported_condition_rules_use_only_configured_label_evidence(
    personalized_client,
    condition,
    label,
    expected_finding_type,
):
    headers = _create_profile(personalized_client, conditions=[condition])

    response = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json=label,
    )

    assert response.status_code == 200
    assessment = response.json()["personal_suitability"]["condition_assessments"][0]
    assert assessment["condition"] == condition
    if expected_finding_type is None:
        assert assessment["findings"] == []
        assert assessment["status"] == "unknown"
        assert any("No condition-specific" in value for value in assessment["missing_information"])
    else:
        assert assessment["findings"]
        assert assessment["findings"][0]["finding_type"] == expected_finding_type


def test_missing_nutrient_values_are_unknown_for_condition_analysis(
    personalized_client,
):
    headers = _create_profile(personalized_client, conditions=["Hypertension"])

    response = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json={"basis": "per_100g"},
    )

    assessment = response.json()["personal_suitability"]["condition_assessments"][0]
    assert assessment["status"] == "unknown"
    assert assessment["findings"] == []
    assert "could not be assessed" in assessment["missing_information"][0]


def test_parsed_extraction_payload_is_accepted_without_losing_field_values(
    personalized_client,
):
    from app.services.label_parser import parse_label_text

    headers = _create_profile(
        personalized_client,
        conditions=["Diabetes", "Celiac disease"],
    )
    extracted = parse_label_text(
        "Per serving\n"
        "Serving Size 30 g\n"
        "Total Sugars 18 g\n"
        "Added Sugar 10 g\n"
        "Sodium 700 mg\n"
        "Saturated Fat 2 g\n"
        "Ingredients: Wheat flour, sugar\n"
        "Contains: wheat"
    )

    response = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json=extracted,
    )

    assert response.status_code == 200
    result = response.json()
    conditions = {
        item["condition"]: item
        for item in result["personal_suitability"]["condition_assessments"]
    }
    assert conditions["Celiac disease"]["findings"]
    assert conditions["Diabetes"]["findings"]
    assert result["general_analysis"]["health_score"]["status"] == "available"


def test_general_score_is_independent_and_existing_anonymous_api_is_unchanged(
    personalized_client,
):
    payload = {
        "sugar_g": 12,
        "added_sugar_g": 7,
        "sodium_mg": 500,
        "saturated_fat_g": 3,
        "basis": "per_serving",
        "serving_size_text": "30 g",
        "sugar_unit": "g",
        "added_sugar_unit": "g",
        "sodium_unit": "mg",
        "saturated_fat_unit": "g",
        "ingredients_text": "sugar, oats",
        "allergens": ["milk"],
    }
    anonymous_response = personalized_client.post("/analyze/label", json=payload)
    assert anonymous_response.status_code == 200
    headers = _create_profile(
        personalized_client,
        conditions=["Diabetes"],
        allergens=["Peanuts"],
    )

    personalized_response = personalized_client.post(
        "/analyze/personalized",
        headers=headers,
        json=payload,
    )
    assert personalized_response.status_code == 200
    result = personalized_response.json()

    assert result["general_analysis"] == anonymous_response.json()
    assert result["personal_suitability"]["status"] == "findings_present"
    assert result["personal_suitability"]["warnings"]


def test_personalized_endpoint_requires_auth_but_existing_label_endpoint_is_public(
    personalized_client,
):
    personalized = personalized_client.post(
        "/analyze/personalized",
        json={"ingredients_text": "peanuts"},
    )
    anonymous_general = personalized_client.post(
        "/analyze/label",
        json={"ingredients_text": "peanuts"},
    )

    assert personalized.status_code == 401
    assert anonymous_general.status_code == 200


def test_users_receive_analysis_only_for_their_own_saved_preferences(
    personalized_client,
):
    peanut_user = _create_profile(
        personalized_client,
        email="peanut@example.com",
        allergens=["Peanuts"],
    )
    sesame_user = _create_profile(
        personalized_client,
        email="sesame@example.com",
        allergens=["Sesame"],
    )
    payload = {"ingredients_text": "peanuts, sesame"}

    peanut_result = personalized_client.post(
        "/analyze/personalized",
        headers=peanut_user,
        json=payload,
    ).json()["personal_suitability"]
    sesame_result = personalized_client.post(
        "/analyze/personalized",
        headers=sesame_user,
        json=payload,
    ).json()["personal_suitability"]

    assert peanut_result["profile_factors"]["allergens"] == ["Peanuts"]
    assert sesame_result["profile_factors"]["allergens"] == ["Sesame"]
    assert {
        finding["allergen"] for finding in peanut_result["detected_concerns"]
    } == {"Peanuts"}
    assert {
        finding["allergen"] for finding in sesame_result["detected_concerns"]
    } == {"Sesame"}
