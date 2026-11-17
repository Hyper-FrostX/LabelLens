from app.services.additive_detector import detect_additives, get_curated_additives


def test_curated_additives_exposes_verification_status_and_scoped_facts():
    all_additives = get_curated_additives()
    assert len(all_additives) == 31

    review_items = get_curated_additives(concern_level="review_required")
    information_items = get_curated_additives(concern_level="informational")

    assert len(review_items) == 29
    assert len(information_items) == 2

    for item in all_additives:
        assert "id" in item
        assert "name" in item
        assert "purpose" in item
        assert "concern_level" in item
        assert item["verification_status"] in {
            "VERIFIED",
            "PROVISIONAL",
            "UNVERIFIED",
            "REVIEW_REQUIRED",
        }
        assert "concern_summary" in item
        assert "evidence_source" in item
        assert "regulatory_status" in item
        assert "synonyms" in item
        assert len(item["synonyms"]) >= 1


def test_get_curated_additives_filter_by_query():
    results = get_curated_additives(query="titanium")
    assert len(results) == 1
    assert results[0]["id"] == "titanium-dioxide"
    assert results[0]["concern_level"] == "review_required"
    assert results[0]["verification_status"] == "REVIEW_REQUIRED"

    e_number_results = get_curated_additives(query="E171")
    assert any(a["id"] == "titanium-dioxide" for a in e_number_results)


def test_unverified_legacy_concern_claims_are_withheld():
    ingredients = [
        "Enriched unbleached wheat flour",
        "potassium bromate",
        "sugar",
        "titanium dioxide",
    ]
    result = detect_additives(ingredients)

    assert result["total_ingredients_scanned"] == 4
    assert result["total_additives_detected"] == 2
    assert result["overall_concern"] == "review_required"
    assert result["counts"]["high"] == 0
    assert result["counts"]["review_required"] == 2
    assert result["counts"]["moderate"] == 0
    assert result["counts"]["low"] == 0

    detected_ids = [a["id"] for a in result["matched_additives"]]
    assert "potassium-bromate" in detected_ids
    assert "titanium-dioxide" in detected_ids
    assert "sugar" in result["unmatched_ingredients"]
    assert all(
        item["concern_summary"].startswith("The previous concern summary is withdrawn")
        for item in result["matched_additives"]
    )


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
    assert result["overall_concern"] == "review_required"
    assert result["counts"]["high"] == 0
    assert result["counts"]["moderate"] == 0
    assert result["counts"]["low"] == 0
    assert result["counts"]["review_required"] == 3

    for additive in result["matched_additives"]:
        assert additive["concern_level"] == "review_required"
        assert "purpose" in additive
        assert "evidence_source" in additive

    assert "does not measure product concentration" in result["guidance_note"]


def test_detect_additives_identifies_moderate_concern_additives():
    ingredients = [
        "carbonated water",
        "sodium benzoate",
        "aspartame",
        "red 40",
    ]
    result = detect_additives(ingredients)

    assert result["total_additives_detected"] == 3
    assert result["overall_concern"] == "review_required"
    assert result["counts"]["high"] == 0
    assert result["counts"]["moderate"] == 0
    assert result["counts"]["review_required"] == 2
    assert result["counts"]["informational"] == 1

    names = [a["name"] for a in result["matched_additives"]]
    assert any("Sodium Benzoate" in name for name in names)
    assert any("Aspartame" in name for name in names)
    assert any("Red 40" in name for name in names)
    aspartame = next(a for a in result["matched_additives"] if a["id"] == "aspartame")
    assert aspartame["verification_status"] == "PROVISIONAL"
    assert "limited evidence" in aspartame["concern_summary"]
    assert "risk from a particular product" in aspartame["concern_summary"]
    assert aspartame["scientific_evidence"]["acceptable_daily_intake"]["value"] == 40
    assert "ADI" not in aspartame["regulatory_status"]


def test_bvo_verified_regulatory_fact_is_limited_to_us_jurisdiction():
    result = detect_additives(["brominated vegetable oil"])

    assert result["overall_concern"] == "informational"
    bvo = result["matched_additives"][0]
    assert bvo["verification_status"] == "VERIFIED"
    assert bvo["regulatory_information"]["jurisdiction"] == "United States"
    assert "other jurisdictions" in bvo["regulatory_status"]


def test_detect_additives_handles_nested_parentheses_and_e_numbers():
    text = "wheat flour, vegetable oil, seasoning (salt, msg, e129, citric acid), titanium dioxide (e171)"
    result = detect_additives(text)

    detected_ids = {a["id"] for a in result["matched_additives"]}
    assert "monosodium-glutamate" in detected_ids
    assert "red-40" in detected_ids
    assert "citric-acid" in detected_ids
    assert "titanium-dioxide" in detected_ids
    assert result["overall_concern"] == "review_required"


def test_detect_additives_with_clean_label_or_empty():
    assert detect_additives([])["total_additives_detected"] == 0
    assert detect_additives(None)["total_additives_detected"] == 0
    assert detect_additives("")["total_additives_detected"] == 0

    clean_result = detect_additives(["100% rolled oats", "almonds", "cinnamon"])
    assert clean_result["total_additives_detected"] == 0
    assert clean_result["overall_concern"] == "none_detected"
    assert len(clean_result["unmatched_ingredients"]) == 3
