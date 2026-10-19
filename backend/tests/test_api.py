import json

import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_endpoint_reports_healthy():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


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
    ],
)
def test_nutrition_endpoint_accepts_valid_request(basis, expected_context):
    response = client.post(
        "/analyze/nutrition",
        json={
            "sugar_g": 10,
            "sodium_mg": 500,
            "saturated_fat_g": 2,
            "basis": basis,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["basis"] == basis
    assert result["percentage_context"] == expected_context
    assert result["sugar_teaspoons"] == 2.5
    assert result["nutrients"]["sugar"]["percentage_of_daily_limit"] == 20
    assert result["nutrients"]["sugar"]["level"] == "caution"
    assert "not official nutritional, health, medical, or regulatory grades" in (
        result["note"]
    )


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
