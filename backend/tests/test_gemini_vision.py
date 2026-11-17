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


def test_fallback_food_suggestions_for_high_sugar_and_sodium():
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
    assert any("Fruit" in name or "Greek Yogurt" in name for name in names)
    assert any("Chickpeas" in name for name in names)
    assert "Crunchy Treat" in advice


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
        assert parsed["additive_analysis"]["total_additives_detected"] == 0
