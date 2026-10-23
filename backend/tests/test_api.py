import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.services import label_ocr
from main import MAX_IMAGE_UPLOAD_BYTES, app


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


def _png_image_bytes() -> bytes:
    image_bytes = BytesIO()
    Image.new("RGB", (2, 2), color="white").save(image_bytes, format="PNG")
    return image_bytes.getvalue()


def test_label_extraction_endpoint_returns_mocked_ocr_results(monkeypatch):
    ocr_text = "\n".join(
        [
            "Product Name: Oat Crunch",
            "Per Serving",
            "Serving Size: 30 g",
            "Total Sugars 8.5 g",
            "Added Sugars 3 g",
            "Sodium 120 mg",
            "Saturated Fat 1.5 g",
            "Ingredients: oats, spices (cinnamon, nutmeg), honey",
        ]
    )
    monkeypatch.setattr(label_ocr, "extract_text", lambda _: ocr_text)

    response = client.post(
        "/extract/label",
        files={"file": ("label.png", _png_image_bytes(), "image/png")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["product_name"]["value"] == "Oat Crunch"
    assert result["basis"] == "per_serving"
    assert result["serving_size_text"] == "30 g"
    assert result["nutrients"]["sugar_g"] == {
        "value": 8.5,
        "unit": "g",
        "source_text": "Total Sugars 8.5 g",
        "confidence": None,
        "needs_review": True,
    }
    assert result["nutrients"]["added_sugar_g"]["value"] == 3
    assert result["ingredients"] == [
        "oats",
        "spices (cinnamon, nutmeg)",
        "honey",
    ]
    assert result["ocr_text"] == ocr_text
    assert "sugar_g" in result["review_required_fields"]


def test_label_extraction_endpoint_requires_a_file():
    response = client.post("/extract/label")

    assert response.status_code == 422


def test_label_extraction_endpoint_rejects_invalid_image_bytes():
    response = client.post(
        "/extract/label",
        files={"file": ("label.png", b"not an image", "image/png")},
    )

    assert response.status_code == 400


def test_label_extraction_endpoint_rejects_unsupported_actual_format():
    image_bytes = BytesIO()
    Image.new("RGB", (2, 2), color="white").save(image_bytes, format="BMP")

    response = client.post(
        "/extract/label",
        files={"file": ("label.jpg", image_bytes.getvalue(), "image/jpeg")},
    )

    assert response.status_code == 415


def test_label_extraction_endpoint_rejects_oversized_upload():
    response = client.post(
        "/extract/label",
        files={
            "file": (
                "label.png",
                b"x" * (MAX_IMAGE_UPLOAD_BYTES + 1),
                "image/png",
            )
        },
    )

    assert response.status_code == 413


def test_label_extraction_endpoint_flags_partial_unreadable_data(monkeypatch):
    monkeypatch.setattr(
        label_ocr,
        "extract_text",
        lambda _: "Nutrition Facts\nIngredients: oats",
    )

    response = client.post(
        "/extract/label",
        files={"file": ("label.png", _png_image_bytes(), "image/png")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["basis"] is None
    assert result["serving_size_text"] is None
    assert result["nutrients"]["sugar_g"]["value"] is None
    assert result["nutrients"]["added_sugar_g"]["value"] is None
    assert result["nutrients"]["sugar_g"]["needs_review"] is True
    assert "basis" in result["review_required_fields"]
    assert "serving_size_text" in result["review_required_fields"]
    assert "sugar_g" in result["review_required_fields"]
    assert "added_sugar_g" in result["review_required_fields"]
    assert result["ingredients"] == ["oats"]


def test_label_extraction_endpoint_reports_unavailable_ocr(monkeypatch):
    def unavailable_ocr(_):
        raise label_ocr.OCRServiceError("Local Tesseract OCR is unavailable.")

    monkeypatch.setattr(label_ocr, "extract_text", unavailable_ocr)

    response = client.post(
        "/extract/label",
        files={"file": ("label.png", _png_image_bytes(), "image/png")},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Local Tesseract OCR is unavailable."


def test_label_analysis_endpoint_returns_nutrients_and_conservative_ingredient_matches():
    response = client.post(
        "/analyze/label",
        json={
            "sugar_g": 10,
            "added_sugar_g": 5,
            "sodium_mg": 1000,
            "saturated_fat_g": 8,
            "basis": "per_serving",
            "serving_size_text": "40 g",
            "sugar_unit": "g",
            "added_sugar_unit": "g",
            "sodium_unit": "mg",
            "saturated_fat_unit": "g",
            "ingredients_text": "Oats, E - 300, SODIUM   BENZOATE, Peanut",
        },
    )

    assert response.status_code == 200
    result = response.json()
    nutrients = result["excess_nutrients"]
    assert nutrients[0]["nutrient"] == "total_sugar"
    assert nutrients[0]["value"] == 10
    assert nutrients[0]["basis"] == "per_serving"
    assert nutrients[1]["nutrient"] == "added_sugar"
    assert nutrients[1]["value"] == 5
    assert nutrients[2]["nutrient"] == "sodium"
    assert nutrients[2]["unit"] == "mg"
    assert nutrients[3]["nutrient"] == "saturated_fat"
    assert result["health_score"]["status"] == "available"
    assert result["health_score"]["data_completeness"]["text"] == (
        "3 of 3 nutrient categories assessed"
    )
    assert 0 <= result["health_score"]["score"] <= 100

    insights = result["ingredient_analysis"]["ingredients"]
    assert insights[1]["matched_name"] == "Ascorbic acid"
    assert (
        insights[1]["concern_level"]
        == "No specific concern identified in current knowledge base"
    )
    assert insights[1]["evidence_source"]
    assert insights[1]["source_url"].startswith("https://")
    assert "not evidence of a specific health risk" in (
        insights[2]["evidence_context"]
    )
    assert insights[2]["concern_status"] == "insufficient_evidence"
    assert insights[3]["concern_level"] == (
        "Established hazard in a specific context"
    )
    assert "peanut allergy" in insights[3]["explanation"]
    assert result["ingredient_analysis"]["evidence_concern_count"] == 1
    assert [
        item["matched_name"]
        for item in result["ingredient_analysis"]["evidence_concerns"]
    ] == ["Peanut"]


def test_label_analysis_accepts_reviewed_per_serving_snack_values():
    response = client.post(
        "/analyze/label",
        json={
            "sugar_g": 3.4,
            "added_sugar_g": 1.5,
            "sodium_mg": 249,
            "saturated_fat_g": 0.8,
            "basis": "per_serving",
            "serving_size_text": "25 g",
            "sugar_unit": "g",
            "added_sugar_unit": "g",
            "sodium_unit": "mg",
            "saturated_fat_unit": "g",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["basis"] == "per_serving"
    assert [
        (item["value"], item["unit"], item["basis"])
        for item in result["excess_nutrients"]
    ] == [
        (3.4, "g", "per_serving"),
        (1.5, "g", "per_serving"),
        (249, "mg", "per_serving"),
        (0.8, "g", "per_serving"),
    ]
    assert all(
        item["status"] != "Unable to assess"
        for item in result["excess_nutrients"]
    )
    assert result["health_score"]["status"] == "available"


def test_label_analysis_expands_nested_spice_additives_without_fuzzy_matching():
    response = client.post(
        "/analyze/label",
        json={
            "ingredients_text": (
                "Rice grits, seasoning (INS 627, INS631), "
                "unclear ingred1ent"
            )
        },
    )

    assert response.status_code == 200
    ingredients = response.json()["ingredient_analysis"]["ingredients"]
    assert [item["matched_name"] for item in ingredients] == [
        "Rice grits",
        None,
        "Disodium guanylate",
        "Disodium inosinate",
        None,
    ]
    assert ingredients[1]["original_label_text"] == "seasoning"
    assert ingredients[-1]["needs_review"] is True


def test_label_analysis_endpoint_marks_missing_nutrients_and_ingredients_unavailable():
    response = client.post("/analyze/label", json={"basis": None})

    assert response.status_code == 200
    result = response.json()
    assert all(
        nutrient["status"] == "Unable to assess"
        and nutrient["value"] is None
        for nutrient in result["excess_nutrients"]
    )
    assert result["ingredient_analysis"]["status"] == "Unavailable"
    assert result["ingredient_analysis"]["needs_review"] is True
    assert result["health_score"]["status"] == "unavailable"
    assert result["health_score"]["score"] is None


def test_label_analysis_endpoint_does_not_guess_ambiguous_basis():
    response = client.post(
        "/analyze/label",
        json={
            "sugar_g": 10,
            "sugar_unit": "g",
            "basis": "per package maybe",
            "serving_size_text": "30 g",
        },
    )

    assert response.status_code == 200
    sugar = response.json()["excess_nutrients"][0]
    assert sugar["status"] == "Unable to assess"
    assert sugar["needs_review"] is True


def test_label_analysis_endpoint_rejects_negative_nutrient_value():
    response = client.post(
        "/analyze/label",
        json={"sugar_g": -0.1, "basis": "per_100g"},
    )

    assert response.status_code == 422


def test_label_analysis_endpoint_flags_unreadable_ingredient_list():
    response = client.post(
        "/analyze/label",
        json={"ingredients_text": "Oats (spices, cinnamon"},
    )

    assert response.status_code == 200
    analysis = response.json()["ingredient_analysis"]
    assert analysis["status"] == "Needs review"
    assert analysis["needs_review"] is True


def test_label_analysis_does_not_classify_every_additive_as_harmful():
    response = client.post(
        "/analyze/label",
        json={"ingredients_text": "Citric acid, Potassium sorbate"},
    )

    assert response.status_code == 200
    results = response.json()["ingredient_analysis"]["ingredients"]
    assert (
        results[0]["concern_level"]
        == "No specific concern identified in current knowledge base"
    )
    assert results[1]["concern_status"] == "insufficient_evidence"
    assert response.json()["ingredient_analysis"]["evidence_concerns"] == []
    assert all(item["concern_level"] != "Harmful" for item in results)


def test_label_analysis_does_not_fuzzy_match_ambiguous_ocr_ingredient():
    response = client.post(
        "/analyze/label",
        json={"ingredients_text": "potasium sorbate"},
    )

    assert response.status_code == 200
    ingredient = response.json()["ingredient_analysis"]["ingredients"][0]
    assert ingredient["matched_name"] is None
    assert ingredient["concern_level"] == "Unrecognized or uncertain"
    assert ingredient["needs_review"] is True
