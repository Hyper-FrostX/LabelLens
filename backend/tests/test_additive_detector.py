import pytest

from app.services.additive_detector import (
    CURATED_ADDITIVES,
    detect_additives,
    get_curated_additives,
)


def test_curated_additives_contains_balanced_concern_levels():
    all_additives = get_curated_additives()
    assert len(all_additives) >= 15

    high_items = get_curated_additives(concern_level="high")
    moderate_items = get_curated_additives(concern_level="moderate")
    low_items = get_curated_additives(concern_level="low")

    assert len(high_items) >= 4
    assert len(moderate_items) >= 6
    assert len(low_items) >= 6

    for item in all_additives:
        assert "id" in item
        assert "name" in item
        assert "purpose" in item
        assert "concern_level" in item
        assert item["concern_level"] in {"low", "moderate", "high"}
        assert "concern_summary" in item
        assert "evidence_source" in item
        assert "regulatory_status" in item
        assert "synonyms" in item
        assert len(item["synonyms"]) >= 1


def test_get_curated_additives_filter_by_query():
    results = get_curated_additives(query="titanium")
    assert len(results) == 1
    assert results[0]["id"] == "titanium-dioxide"
    assert results[0]["concern_level"] == "high"

    e_number_results = get_curated_additives(query="E171")
    assert any(a["id"] == "titanium-dioxide" for a in e_number_results)


def test_detect_additives_identifies_high_concern_compounds():
    ingredients = [
        "Enriched unbleached wheat flour",
        "potassium bromate",
        "sugar",
        "titanium dioxide",
    ]
    result = detect_additives(ingredients)

    assert result["total_ingredients_scanned"] == 4
    assert result["total_additives_detected"] == 2
    assert result["overall_concern"] == "high"
    assert result["counts"]["high"] == 2
    assert result["counts"]["moderate"] == 0
    assert result["counts"]["low"] == 0

    detected_ids = [a["id"] for a in result["matched_additives"]]
    assert "potassium-bromate" in detected_ids
    assert "titanium-dioxide" in detected_ids
    assert "sugar" in result["unmatched_ingredients"]


def test_detect_additives_avoids_calling_safe_additives_harmful():
    ingredients = [
        "water",
        "organic oats",
        "citric acid",
        "ascorbic acid",
        "soy lecithin",
    ]
    result = detect_additives(ingredients)

    assert result["total_additives_detected"] == 3
    assert result["overall_concern"] == "low"
    assert result["counts"]["high"] == 0
    assert result["counts"]["moderate"] == 0
    assert result["counts"]["low"] == 3

    for additive in result["matched_additives"]:
        assert additive["concern_level"] == "low"
        assert "purpose" in additive
        assert "evidence_source" in additive

    assert "Not every additive is harmful" in result["guidance_note"]


def test_detect_additives_identifies_moderate_concern_additives():
    ingredients = [
        "carbonated water",
        "sodium benzoate",
        "aspartame",
        "red 40",
    ]
    result = detect_additives(ingredients)

    assert result["total_additives_detected"] == 3
    assert result["overall_concern"] == "moderate"
    assert result["counts"]["high"] == 0
    assert result["counts"]["moderate"] == 3

    names = [a["name"] for a in result["matched_additives"]]
    assert any("Sodium Benzoate" in name for name in names)
    assert any("Aspartame" in name for name in names)
    assert any("Red 40" in name for name in names)


def test_detect_additives_handles_nested_parentheses_and_e_numbers():
    text = "wheat flour, vegetable oil, seasoning (salt, msg, e129, citric acid), titanium dioxide (e171)"
    result = detect_additives(text)

    detected_ids = {a["id"] for a in result["matched_additives"]}
    assert "monosodium-glutamate" in detected_ids
    assert "red-40" in detected_ids
    assert "citric-acid" in detected_ids
    assert "titanium-dioxide" in detected_ids
    assert result["overall_concern"] == "high"


def test_detect_additives_with_clean_label_or_empty():
    assert detect_additives([])["total_additives_detected"] == 0
    assert detect_additives(None)["total_additives_detected"] == 0
    assert detect_additives("")["total_additives_detected"] == 0

    clean_result = detect_additives(["100% rolled oats", "almonds", "cinnamon"])
    assert clean_result["total_additives_detected"] == 0
    assert clean_result["overall_concern"] == "none_detected"
    assert len(clean_result["unmatched_ingredients"]) == 3
