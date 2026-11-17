import secrets

from fastapi.testclient import TestClient

from app.database.config import get_db, get_optional_db
from app.models import Allergen, User, UserAllergen
from app.security.tokens import create_access_token
from main import app

client = TestClient(app)


def test_product_analysis_composes_existing_services_and_keeps_declarations_distinct():
    response = client.post(
        "/analyze/product",
        json={
            "product_name": "Oat snack",
            "sugar_g": 10,
            "added_sugar_g": 4,
            "sodium_mg": 500,
            "saturated_fat_g": 2,
            "basis": "per_100g",
            "sugar_unit": "g",
            "added_sugar_unit": "g",
            "sodium_unit": "mg",
            "saturated_fat_unit": "g",
            "ingredients_text": "Oats, milk powder, E 300, potassium sorbate",
            "allergens": ["Soy"],
            "may_contain": ["Peanuts"],
            "explanation_level": "detailed",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["product"]["name"] == "Oat snack"
    assert result["nutrition"]["health_score"]["score"] == 82
    assert result["nutrition"]["health_score"]["score"] == client.post(
        "/analyze/label",
        json={
            "sugar_g": 10,
            "added_sugar_g": 4,
            "sodium_mg": 500,
            "saturated_fat_g": 2,
            "basis": "per_100g",
            "sugar_unit": "g",
            "added_sugar_unit": "g",
            "sodium_unit": "mg",
            "saturated_fat_unit": "g",
        },
    ).json()["health_score"]["score"]
    verification = result["ingredients"]["verification_statuses"]
    assert verification["ingredients"]
    assert verification["additives"]
    assert all(
        item["verification_status"] in {
            "VERIFIED",
            "PROVISIONAL",
            "REVIEW_REQUIRED",
            "UNVERIFIED",
        }
        for item in verification["ingredients"] + verification["additives"]
    )
    assert result["allergen_analysis"]["declared_allergens"]["label_text"] == ["Soy"]
    assert result["allergen_analysis"]["may_contain"]["label_text"] == ["Peanuts"]
    assert result["allergen_analysis"]["declared_allergens"]["matches"][0]["source"] == (
        "declared_allergen"
    )
    assert result["allergen_analysis"]["may_contain"]["matches"][0]["source"] == (
        "may_contain"
    )
    assert result["allergen_analysis"]["personal_suitability"]["status"] == (
        "NOT_EVALUATED"
    )
    assert result["alternatives"]["status"] == "NOT_AVAILABLE"
    scores = result["food_intelligence"]["scores"]["scores"]
    assert scores["nutrition_quality"]["status"] == "available"
    assert scores["protein_quality"]["status"] == "insufficient_data"
    assert scores["ingredient_transparency"]["score"] == 100
    assert result["food_intelligence"]["personal_suitability"]["status"] == (
        "INSUFFICIENT_INFORMATION"
    )
    assert result["food_intelligence"]["nutrition"]["normalized_basis"] == "per_100g"
    assert result["completeness"]["status"] == "complete_for_submitted_fields"
    assert "not medical advice" in result["note"]
    assert "FSSAI score" not in result["note"]


def test_product_analysis_reports_unavailable_score_and_missing_inputs():
    response = client.post("/analyze/product", json={})

    assert response.status_code == 200
    result = response.json()
    assert result["nutrition"]["health_score"]["status"] == "unavailable"
    assert result["nutrition"]["health_score"]["score"] is None
    assert "ingredients" in result["completeness"]["missing_fields"]
    assert result["allergen_analysis"]["declared_allergens"]["status"] == (
        "not_provided"
    )
    assert result["allergen_analysis"]["may_contain"]["status"] == "not_provided"


def test_product_question_answers_only_supported_context_intents():
    context = {
        "product": {"name": "Oat snack"},
        "nutrition": {
            "basis": "per_100g",
            "excess_nutrients": [],
            "health_score": {"status": "unavailable", "score": None},
        },
        "ingredients": {
            "analysis": {"ingredients": []},
            "additive_analysis": {"matched_additives": []},
            "verification_statuses": {"ingredients": [], "additives": []},
        },
        "allergen_analysis": {
            "declared_allergens": {"label_text": ["Milk"], "matches": []},
            "may_contain": {"label_text": ["Peanuts"], "matches": []},
            "personal_suitability": {"status": "NOT_EVALUATED"},
        },
        "alternatives": {"status": "NOT_AVAILABLE"},
    }

    allergens = client.post(
        "/analyze/product/question",
        json={"question": "Does it say may contain peanuts?", "context": context},
    ).json()
    assert allergens["intent"] == "allergens"
    assert allergens["status"] == "answered"
    assert allergens["evidence"]["declared_allergens"] == ["Milk"]
    assert allergens["evidence"]["may_contain"] == ["Peanuts"]

    unknown = client.post(
        "/analyze/product/question",
        json={"question": "Will it cure my illness?", "context": context},
    ).json()
    assert unknown["status"] == "unknown"
    assert "not provide medical advice" in unknown["answer"]

    missing = client.post(
        "/analyze/product/question",
        json={"question": "What is the carbon footprint?", "context": context},
    ).json()
    assert missing["intent"] == "unsupported"
    assert missing["status"] == "unknown"

    diabetes = client.post(
        "/analyze/product/ask",
        json={
            "question": "Is this suitable for someone with diabetes?",
            "context": {
                "personalized_suitability": {"status": "NOT_EVALUATED"},
            },
            "explanation_level": "detailed",
        },
    ).json()
    assert diabetes["intent"] == "personal_suitability"
    assert diabetes["status"] == "unknown"
    assert "medical advice" in diabetes["answer"]
    assert diabetes["limitations"]

    limitations = client.post(
        "/analyze/product/ask",
        json={
            "question": "What are the limitations?",
            "context": {"limitations": ["Ingredients text is unavailable."]},
        },
    ).json()
    assert limitations["intent"] == "limitations"
    assert limitations["evidence"] == ["Ingredients text is unavailable."]

    additive_code = client.post(
        "/analyze/product/ask",
        json={"question": "What does INS 621 mean?", "context": {}},
    ).json()
    assert additive_code["intent"] == "additive_code"
    assert additive_code["status"] == "answered"
    assert additive_code["evidence"]["verification_status"] in {
        "VERIFIED",
        "PROVISIONAL",
        "REVIEW_REQUIRED",
        "UNVERIFIED",
    }


def test_product_question_requires_bounded_context():
    response = client.post(
        "/analyze/product/question",
        json={"question": "What is the score?", "context": {"text": "x" * 50_001}},
    )

    assert response.status_code == 422


def test_product_ask_endpoint_uses_optional_provider_without_exposing_key(
    monkeypatch,
):
    from app.services import product_assistant

    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("AI_API_KEY", "server-only-test-key")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setenv("AI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setattr(
        product_assistant,
        "_request_provider",
        lambda **_kwargs: {
            "intent": "product_question",
            "status": "answered",
            "answer": "The submitted product is an oat snack.",
            "evidence": [{"path": "/product/name", "value": "Oat snack"}],
            "missing_information": [],
            "limitations": ["AI output is not independently verified."],
            "response_mode": "AI_GENERATED",
            "provider_status": "AVAILABLE",
            "provider": "openai",
            "model": "test-model",
        },
    )

    response = client.post(
        "/analyze/product/ask",
        json={
            "question": "What is this product?",
            "context": {"product": {"name": "Oat snack"}},
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["response_mode"] == "AI_GENERATED"
    assert result["evidence"][0]["value"] == "Oat snack"
    assert "server-only-test-key" not in response.text


def test_product_alternatives_use_only_matching_stored_nutrients():
    response = client.post(
        "/analyze/product",
        json={
            "product_name": "Current bar",
            "basis": "per_100g",
            "sugar_g": 20,
            "sugar_unit": "g",
            "sodium_mg": 500,
            "sodium_unit": "mg",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["alternatives"]["status"] == "NOT_AVAILABLE"

    from app.schemas.product_analysis import ProductAnalysisInput
    from app.services.product_analysis import _report_alternatives

    data = ProductAnalysisInput(
        product_name="Current bar",
        basis="per_100g",
        sugar_g=20,
        sugar_unit="g",
        sodium_mg=500,
        sodium_unit="mg",
    )
    alternatives = _report_alternatives(
        data,
        [
            {
                "product_name": "Stored bar",
                "input": {
                    "product_name": "Stored bar",
                    "basis": "per_100g",
                    "sugar_g": 10,
                    "sugar_unit": "g",
                    "sodium_mg": 400,
                    "sodium_unit": "mg",
                },
            },
            {
                "product_name": "Noncomparable",
                "input": {
                    "product_name": "Noncomparable",
                    "basis": "per_100ml",
                    "sugar_g": 1,
                    "sugar_unit": "g",
                    "sodium_mg": 1,
                    "sodium_unit": "mg",
                },
            },
        ],
    )
    assert alternatives["status"] == "POTENTIAL_ALTERNATIVES"
    assert [item["product"] for item in alternatives["items"]] == ["Stored bar"]
    assert alternatives["items"][0]["tradeoffs"] == []


def test_authenticated_product_analysis_saves_and_lists_scan_history(
    db_session,
    monkeypatch,
):
    secret = secrets.token_urlsafe(48)
    monkeypatch.setenv("JWT_SECRET_KEY", secret)
    user = User(
        name="History User",
        email="history@example.com",
        password_hash="unused-test-hash",
    )
    db_session.add(user)
    db_session.flush()
    token, _ = create_access_token(user.id)

    def override_session():
        yield db_session

    previous_db = app.dependency_overrides.get(get_db)
    previous_optional_db = app.dependency_overrides.get(get_optional_db)
    app.dependency_overrides[get_db] = override_session
    app.dependency_overrides[get_optional_db] = override_session
    try:
        with TestClient(app) as authenticated_client:
            response = authenticated_client.post(
                "/analyze/product",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "product_name": "Saved oat bar",
                    "ingredients_text": "oats, honey",
                    "save_to_history": True,
                },
            )
            assert response.status_code == 200
            scan_id = response.json()["saved_scan_id"]

            history = authenticated_client.get(
                "/scans",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert history.status_code == 200
            scans = history.json()
            assert len(scans) == 1
            assert scans[0]["id"] == scan_id
            assert scans[0]["extracted_label"]["extracted_data"]["product_name"] == (
                "Saved oat bar"
            )
    finally:
        if previous_db is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_db
        if previous_optional_db is None:
            app.dependency_overrides.pop(get_optional_db, None)
        else:
            app.dependency_overrides[get_optional_db] = previous_optional_db


def test_authenticated_profile_drives_product_suitability(
    db_session,
    monkeypatch,
):
    secret = secrets.token_urlsafe(48)
    monkeypatch.setenv("JWT_SECRET_KEY", secret)
    user = User(
        name="Allergy User",
        email="allergy@example.com",
        password_hash="unused-test-hash",
    )
    peanut = Allergen(name="Peanuts", category="major")
    user.allergen_selections = [UserAllergen(allergen=peanut)]
    db_session.add(user)
    db_session.flush()
    token, _ = create_access_token(user.id)

    def override_session():
        yield db_session

    previous_optional_db = app.dependency_overrides.get(get_optional_db)
    app.dependency_overrides[get_optional_db] = override_session
    try:
        with TestClient(app) as authenticated_client:
            response = authenticated_client.post(
                "/analyze/product",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "ingredients_text": "peanut flour, sugar",
                    "basis": "per_100g",
                },
            )
        assert response.status_code == 200
        result = response.json()
        assert result["personalized_suitability"]["status"] == "UNSUITABLE"
        assert result["allergen_analysis"]["personal_suitability"]["details"][
            "profile_factors"
        ]["allergens"] == ["Peanuts"]
    finally:
        if previous_optional_db is None:
            app.dependency_overrides.pop(get_optional_db, None)
        else:
            app.dependency_overrides[get_optional_db] = previous_optional_db
