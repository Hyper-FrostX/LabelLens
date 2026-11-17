import secrets
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.config import get_db
from app.models import (
    Allergen,
    HealthCondition,
    User,
    UserAllergen,
    UserHealthCondition,
)
from app.security.tokens import JWT_ALGORITHM, create_access_token
from main import app


@pytest.fixture
def auth_client(db_engine, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")

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


def _register(client: TestClient, email="person@example.com", password="StrongPass123!"):
    return client.post(
        "/auth/register",
        json={"name": "Test Person", "email": email, "password": password},
    )


def _login(client: TestClient, email="person@example.com", password="StrongPass123!"):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_register_hashes_password_and_returns_public_user(auth_client, db_engine):
    response = _register(auth_client)

    assert response.status_code == 201
    user_data = response.json()
    assert user_data["email"] == "person@example.com"
    assert "password_hash" not in user_data
    with Session(db_engine) as session:
        user = session.scalar(select(User).where(User.email == "person@example.com"))
        assert user is not None
        assert user.password_hash != "StrongPass123!"
        assert user.password_hash.startswith("$argon2id$")
        assert user.health_profile is not None


def test_registration_rejects_duplicate_email_case_insensitively(auth_client):
    assert _register(auth_client).status_code == 201

    duplicate = _register(auth_client, email="PERSON@EXAMPLE.COM")

    assert duplicate.status_code == 409
    assert "password_hash" not in duplicate.text


def test_registration_validates_email_and_password(auth_client):
    invalid_email = auth_client.post(
        "/auth/register",
        json={
            "name": "Test Person",
            "email": "not-an-email",
            "password": "StrongPass123!",
        },
    )
    short_password = auth_client.post(
        "/auth/register",
        json={
            "name": "Test Person",
            "email": "person@example.com",
            "password": "short",
        },
    )

    assert invalid_email.status_code == 422
    assert short_password.status_code == 422


def test_login_issues_token_and_me_returns_authenticated_user(auth_client):
    assert _register(auth_client).status_code == 201

    login_response = auth_client.post(
        "/auth/login",
        json={"email": "PERSON@example.com", "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["expires_in"] == 15 * 60
    token = login_response.json()["access_token"]
    me = auth_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me.status_code == 200
    assert me.json()["name"] == "Test Person"
    assert me.json()["email"] == "person@example.com"
    assert "password_hash" not in me.json()


def test_login_uses_same_error_for_unknown_email_and_wrong_password(auth_client):
    assert _register(auth_client).status_code == 201

    wrong_password = auth_client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "WrongPassword123!"},
    )
    unknown_email = auth_client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "WrongPassword123!"},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


@pytest.mark.parametrize(
    "token_factory",
    [
        lambda secret: "not.a.jwt",
        lambda secret: jwt.encode(
            {
                "sub": "1",
                "token_type": "access",
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            secret,
            algorithm=JWT_ALGORITHM,
        ),
        lambda secret: jwt.encode(
            {
                "sub": "1",
                "token_type": "access",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            "different-test-secret-that-is-long-enough",
            algorithm=JWT_ALGORITHM,
        ),
    ],
)
def test_invalid_or_expired_tokens_are_rejected(auth_client, token_factory):
    import os

    token = token_factory(os.environ["JWT_SECRET_KEY"])

    response = auth_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_token_creation_requires_an_explicit_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_access_token(1)


@pytest.mark.parametrize("path", ["/auth/me", "/profile"])
def test_protected_endpoints_require_authentication(auth_client, path):
    response = auth_client.get(path)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_profile_is_created_read_and_updated_with_catalog_and_custom_values(
    auth_client,
    db_engine,
):
    registered = _register(auth_client)
    assert registered.status_code == 201
    token = _login(auth_client)
    headers = {"Authorization": f"Bearer {token}"}

    initial = auth_client.get("/profile", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["expertise_level"] == "beginner"
    assert initial.json()["health_conditions"] == []

    updated = auth_client.put(
        "/profile",
        headers=headers,
        json={
            "name": "Updated Person",
            "expertise_level": "EXPERT",
            "health_conditions": ["Diabetes", "hypertension", "DIABETES"],
            "allergens": ["gluten", "Peanuts", "PEANUTS"],
            "custom_allergens": ["Mustard", " mustard ", "Pine nuts"],
            "dietary_preferences": ["vegetarian", "VEGAN"],
            "ingredient_exclusions": ["Palm oil", " palm oil ", "Gelatin"],
            "nutrition_goals": ["lower_sugar", "higher_protein"],
            "calorie_goal_kcal": 2000,
            "protein_goal_g": 80,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Person"
    assert updated.json()["expertise_level"] == "expert"
    assert updated.json()["health_conditions"] == ["Diabetes", "Hypertension"]
    assert updated.json()["allergens"] == ["Gluten", "Peanuts"]
    assert updated.json()["custom_allergens"] == ["Mustard", "Pine nuts"]
    assert updated.json()["dietary_preferences"] == ["Vegetarian", "Vegan"]
    assert updated.json()["ingredient_exclusions"] == ["Palm oil", "Gelatin"]
    assert updated.json()["nutrition_goals"] == ["lower_sugar", "higher_protein"]
    assert updated.json()["calorie_goal_kcal"] == 2000
    assert updated.json()["protein_goal_g"] == 80

    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(HealthCondition)) == 2
        assert session.scalar(select(func.count()).select_from(Allergen)) == 2
        assert (
            session.scalar(select(func.count()).select_from(UserHealthCondition))
            == 2
        )
        assert session.scalar(select(func.count()).select_from(UserAllergen)) == 4

    persisted = auth_client.get("/profile", headers=headers)
    assert persisted.json() == updated.json()


def test_profile_updates_are_scoped_to_authenticated_user(auth_client):
    first_user = _register(auth_client)
    first_user_id = first_user.json()["id"]
    first_token = _login(auth_client)
    first_headers = {"Authorization": f"Bearer {first_token}"}
    auth_client.put(
        "/profile",
        headers=first_headers,
        json={
            "name": "First Person",
            "expertise_level": "beginner",
            "health_conditions": ["Diabetes"],
            "allergens": ["Gluten"],
            "custom_allergens": [],
        },
    )

    assert (
        _register(
            auth_client,
            email="second@example.com",
        ).status_code
        == 201
    )
    second_token = _login(auth_client, email="second@example.com")
    second_headers = {"Authorization": f"Bearer {second_token}"}

    second_profile = auth_client.get(
        f"/profile?user_id={first_user_id}",
        headers=second_headers,
    )

    assert second_profile.status_code == 200
    assert second_profile.json()["name"] == "Test Person"
    assert second_profile.json()["health_conditions"] == []
    assert second_profile.json()["allergens"] == []
    first_profile = auth_client.get("/profile", headers=first_headers)
    assert first_profile.json()["name"] == "First Person"
    assert first_profile.json()["health_conditions"] == ["Diabetes"]


@pytest.mark.parametrize(
    "invalid_field,invalid_value",
    [
        ("expertise_level", "medical"),
        ("health_conditions", ["Unknown condition"]),
        ("allergens", ["Unknown allergen"]),
        ("custom_allergens", ["gluten"]),
        ("dietary_preferences", ["Carnivore"]),
        ("nutrition_goals", ["cure_diabetes"]),
        ("calorie_goal_kcal", 200),
        ("calorie_goal_kcal", "NaN"),
        ("protein_goal_g", 500),
        ("protein_goal_g", "inf"),
    ],
)
def test_invalid_profile_values_do_not_change_saved_profile(
    auth_client,
    invalid_field,
    invalid_value,
):
    assert _register(auth_client).status_code == 201
    token = _login(auth_client)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "Changed Name",
        "expertise_level": "expert",
        "health_conditions": [],
        "allergens": [],
        "custom_allergens": [],
    }
    payload[invalid_field] = invalid_value

    invalid = auth_client.put("/profile", headers=headers, json=payload)

    assert invalid.status_code == 422
    profile = auth_client.get("/profile", headers=headers)
    assert profile.json()["name"] == "Test Person"
    assert profile.json()["health_conditions"] == []
