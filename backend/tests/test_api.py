import json

import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_endpoint_reports_healthy():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_nutrition_endpoint_accepts_valid_request():
    response = client.post(
        "/analyze/nutrition",
        json={
            "sugar_g": 10,
            "sodium_mg": 500,
            "saturated_fat_g": 2,
            "basis": "per_serving",
        },
    )

    assert response.status_code == 200
    assert response.json()["basis"] == "per_serving"
    assert response.json()["sugar_teaspoons"] == 2.5
    assert response.json()["nutrients"]["sugar"]["level"] == "caution"


def test_nutrition_endpoint_accepts_missing_nutrients():
    response = client.post(
        "/analyze/nutrition",
        json={"basis": "per_100g"},
    )

    assert response.status_code == 200
    assert response.json()["sugar_teaspoons"] is None
    assert response.json()["nutrients"]["sugar"]["level"] == "unknown"


@pytest.mark.parametrize(
    "nutrient",
    ["sugar_g", "sodium_mg", "saturated_fat_g"],
)
def test_nutrition_endpoint_rejects_negative_values(nutrient):
    response = client.post(
        "/analyze/nutrition",
        json={nutrient: -1, "basis": "per_serving"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "json_value",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
@pytest.mark.parametrize(
    "nutrient",
    ["sugar_g", "sodium_mg", "saturated_fat_g"],
)
def test_nutrition_endpoint_rejects_non_finite_values(
    nutrient, json_value
):
    body = json.dumps(
        {nutrient: json_value, "basis": "per_serving"}
    )
    response = client.post(
        "/analyze/nutrition",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
