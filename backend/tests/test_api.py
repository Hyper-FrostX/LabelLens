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
        "source_text": "Total Sugars 8.5 g",
        "confidence": None,
        "needs_review": True,
    }
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
    assert result["nutrients"]["sugar_g"]["needs_review"] is True
    assert "basis" in result["review_required_fields"]
    assert "serving_size_text" in result["review_required_fields"]
    assert "sugar_g" in result["review_required_fields"]
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


def test_knowledge_base_endpoint_returns_additives_and_filters():
    # Test full knowledge base
    response = client.get("/additives/knowledge-base")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 15
    assert len(data["additives"]) == data["total"]

    # Filter by concern level
    resp_high = client.get("/additives/knowledge-base?concern_level=high")
    assert resp_high.status_code == 200
    high_data = resp_high.json()
    assert all(a["concern_level"] == "high" for a in high_data["additives"])

    # Search query
    resp_search = client.get("/additives/knowledge-base?query=ascorbic")
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert any("Ascorbic Acid" in a["name"] for a in search_data["additives"])


def test_analyze_ingredients_endpoint_with_list():
    response = client.post(
        "/analyze/ingredients",
        json={
            "ingredients": [
                "corn syrup",
                "titanium dioxide",
                "citric acid",
                "red 40",
            ]
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["total_ingredients_scanned"] == 4
    assert result["total_additives_detected"] == 3
    assert result["overall_concern"] == "high"
    assert result["counts"]["high"] == 1
    assert result["counts"]["moderate"] == 1
    assert result["counts"]["low"] == 1

    # Verify each additive has required fields
    for item in result["matched_additives"]:
        assert "purpose" in item
        assert "concern_level" in item
        assert "evidence_source" in item
        assert "regulatory_status" in item


def test_analyze_ingredients_endpoint_with_text():
    response = client.post(
        "/analyze/ingredients",
        json={"ingredients_text": "whole oats, salt, soy lecithin, calcium propionate"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["total_additives_detected"] == 2
    assert result["overall_concern"] == "low"
    assert result["counts"]["low"] == 2
    assert "Not every additive is harmful" in result["guidance_note"]
