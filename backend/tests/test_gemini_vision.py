from io import BytesIO
from unittest.mock import MagicMock, patch

from PIL import Image

from app.services import gemini_vision


def _sample_png(size=(100, 100), color="white") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_prepare_image_for_gemini_resizes_oversized():
    large_bytes = _sample_png(size=(3000, 1500))
    mime_type, b64 = gemini_vision.prepare_image_for_gemini(large_bytes)
    assert mime_type == "image/jpeg"
    assert len(b64) > 0


def test_gemini_vision_reuses_shared_provider_configuration(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("AI_API_KEY", "shared-test-key")
    monkeypatch.setenv("AI_MODEL", "gemini-test-model")
    monkeypatch.setenv("GEMINI_API_KEY", "legacy-test-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    assert gemini_vision.get_gemini_api_key() == "shared-test-key"
    assert gemini_vision.get_candidate_models()[0] == "gemini-test-model"


def test_fallback_food_suggestions_are_deterministic_general_ideas():
    nutrients = {
        "sugar_g": 18.0,
        "added_sugar_g": 14.0,
        "sodium_mg": 520.0,
        "saturated_fat_g": 4.5,
    }
    suggestions, advice = gemini_vision.generate_fallback_food_suggestions(
        product_name="Crunchy Treat",
        nutrients=nutrients,
        ingredients_text="Sugar, salt, palm oil",
    )
    assert len(suggestions) > 0
    names = [s["name"] for s in suggestions]
    assert any("Oats" in name for name in names)
    assert "general, non-personalized" in advice
    assert "Crunchy Treat" not in advice


def test_fallback_suggestions_do_not_depend_on_basis():
    nutrient_values = {
        "sugar_g": 18.0,
        "added_sugar_g": 14.0,
        "sodium_mg": 520.0,
        "saturated_fat_g": 4.5,
    }
    results = [
        gemini_vision.generate_fallback_food_suggestions(
            product_name="Snack",
            nutrients={**nutrient_values, **basis_data},
            ingredients_text=None,
        )
        for basis_data in (
            {},
            {"basis": "per_serving"},
            {"basis": "unknown"},
            {"basis": None},
        )
    ]
    assert all(result == results[0] for result in results[1:])


def test_fallback_suggestions_are_general_and_do_not_claim_nutrient_values():
    suggestions, advice = gemini_vision.generate_fallback_food_suggestions(
        product_name="Snack",
        nutrients={
            "sugar_g": 18.0,
            "added_sugar_g": 14.0,
            "sodium_mg": 520.0,
            "saturated_fat_g": 4.5,
        },
        ingredients_text=None,
    )
    text = " ".join(
        [advice]
        + [
            f"{item['name']} {item['category']} {item['reason']} "
            + " ".join(item["highlights"])
            for item in suggestions
        ]
    ).casefold()
    assert "general, non-personalized" in advice
    assert "matched alternative nutrient values" in advice
    assert "not measured or healthier substitutes" in advice
    assert "%" not in text
    assert "zero" not in text
    assert "0g" not in text


def test_fallback_suggestions_make_missing_nutrients_explicit():
    suggestions, advice = gemini_vision.generate_fallback_food_suggestions(
        product_name=None,
        nutrients={"sugar_g": None, "sodium_mg": {"value": None}},
        ingredients_text=None,
    )
    assert suggestions
    assert "Label data is unavailable" in advice
    assert "sugars" in advice
    assert "sodium" in advice
    assert "added sugars" in advice
    assert "saturated fat" in advice


def test_unmatched_and_incomparable_suggestion_claims_are_discarded():
    suggestions = gemini_vision._normalize_food_suggestions(
        [
            {
                "name": "70% Less Sodium Herb-Roasted Chickpeas",
                "category": "70% less sodium per 100 g",
                "reason": "Lower sodium than this per-serving product.",
                "highlights": ["Zero added sugar"],
                "comparison": {
                    "product": {"sodium_mg": 500, "basis": "per_serving"},
                    "alternative": {"sodium_mg": 150, "basis": "per_100g"},
                },
            },
            {
                "name": "Greek Yogurt with Fruit",
                "category": "Whole Food Swap",
                "reason": "0g added sugar and 20% less sugar.",
                "highlights": ["High protein"],
            },
        ]
    )
    assert [item["name"] for item in suggestions] == ["Greek Yogurt with Fruit"]
    assert suggestions[0]["category"] == "General food idea"
    assert "not a measured comparison" in suggestions[0]["reason"]
    assert suggestions[0]["highlights"] == ["General idea"]
    assert "70%" not in suggestions[0]["reason"]
    assert "0g" not in suggestions[0]["reason"]


def test_call_gemini_vision_falls_back_on_429():
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.text = "Quota exceeded"

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": """
                            {
                                "product_name": "Organic Almond Milk",
                                "serving_size_text": "240 ml",
                                "basis": "per_serving",
                                "nutrients": {
                                    "sugar_g": 0.0,
                                    "added_sugar_g": 0.0,
                                    "sodium_mg": 120.0,
                                    "saturated_fat_g": 0.5
                                },
                                "ingredients_text": "Filtered water, almonds, sea salt",
                                "ingredients": ["Filtered water", "almonds", "sea salt"],
                                "food_suggestions": [
                                    {
                                        "name": "Homemade Cashew Milk",
                                        "category": "Whole Food Swap",
                                        "reason": "Freshly blended whole nuts with no packaging waste.",
                                        "highlights": ["0g Added Sugar", "Raw & Unprocessed"]
                                    }
                                ],
                                "dietary_advice": "Great unsweetened beverage option.",
                                "raw_text_summary": "Organic Almond Milk Unsweetened"
                            }
                            """
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.Client.post", side_effect=[mock_429, mock_200]) as mock_post:
        result = gemini_vision.call_gemini_vision(
            mime_type="image/jpeg",
            base64_data="dummy",
            api_key="test_key",
            models=["model-fail", "model-pass"],
        )
        assert result["product_name"] == "Organic Almond Milk"
        assert result["_model_used"] == "model-pass"
        assert len(result["food_suggestions"]) == 1
        assert "test_key" not in mock_post.call_args_list[0].args[0]
        assert (
            mock_post.call_args_list[0].kwargs["headers"]["x-goog-api-key"]
            == "test_key"
        )


def test_extract_label_with_vision_returns_full_structure():
    mock_vision_data = {
        "product_name": "Berry Granola",
        "serving_size_text": "40 g",
        "basis": "per_serving",
        "nutrients": {
            "sugar_g": 6.0,
            "added_sugar_g": 2.0,
            "sodium_mg": 90.0,
            "saturated_fat_g": 1.0,
        },
        "ingredients_text": "Rolled oats, dried berries, honey",
        "ingredients": ["Rolled oats", "dried berries", "honey"],
        "food_suggestions": [
            {
                "name": "Steel Cut Oats with Fresh Berries",
                "category": "Whole Food Swap",
                "reason": "Lower glycemic impact and zero processed sweeteners.",
                "highlights": ["0g Added Sugar", "High Fiber"],
            }
        ],
        "dietary_advice": "High in whole grains.",
        "raw_text_summary": "Berry Granola 40g",
        "_model_used": "gemini-2.5-flash",
    }

    with (
        patch.object(
            gemini_vision,
            "call_gemini_vision",
            return_value=mock_vision_data,
        ),
        patch.dict(
            gemini_vision.os.environ,
            {
                "AI_PROVIDER": "none",
                "GEMINI_API_KEY": "fake_key",
                "DISABLE_GEMINI_VISION": "false",
            },
        ),
    ):
        parsed = gemini_vision.extract_label_with_vision(_sample_png())
        assert parsed["product_name"]["value"] == "Berry Granola"
        assert parsed["nutrients"]["sugar_g"]["value"] == 6.0
        assert parsed["nutrients"]["sugar_g"]["confidence"] is None
        assert parsed["nutrients"]["sugar_g"]["needs_review"] is True
        assert parsed["nutrients"]["sodium_mg"]["unit"] == "mg"
        assert parsed["vision_provider"] == "gemini"
        assert len(parsed["food_suggestions"]) == 1
        assert parsed["food_suggestions"][0]["name"] == "Steel Cut Oats with Fresh Berries"
        assert parsed["food_suggestions"][0]["category"] == "General food idea"
        assert "general, non-personalized" in parsed["dietary_advice"]
        assert parsed["additive_analysis"]["total_additives_detected"] == 0
