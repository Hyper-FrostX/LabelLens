import json
from datetime import date

from fastapi.testclient import TestClient

from app.services.label_compliance import analyze_label_compliance
from main import app

client = TestClient(app)


def test_fssai_format_is_separate_from_official_verification():
    report = analyze_label_compliance("FSSAI License No: 12345678901234")
    license_info = report["fssai_license_information"]

    assert license_info["extracted_number"] == "12345678901234"
    assert license_info["normalized_number"] == "12345678901234"
    assert license_info["format_valid"] is True
    assert license_info["official_verification_status"] == "NOT_VERIFIED"
    assert "no lookup performed" in license_info["verification_source"]
    assert license_info["confidence"] is None


def test_fssai_ocr_corrections_and_malformed_candidates_require_manual_review():
    corrected = analyze_label_compliance("FSSAI Regn No: 12O45678901234")[
        "fssai_license_information"
    ]
    malformed = analyze_label_compliance("FSSAI License No: 12345")[
        "fssai_license_information"
    ]
    ambiguous = analyze_label_compliance(
        "FSSAI License No: 12345678901234\nFSSAI License No: 98765432109876"
    )["fssai_license_information"]

    assert corrected["extracted_number"] == "12O45678901234"
    assert corrected["normalized_number"] == "12045678901234"
    assert corrected["format_valid"] is True
    assert corrected["official_verification_status"] == "NEEDS_MANUAL_REVIEW"
    assert malformed["normalized_number"] == "12345"
    assert malformed["format_valid"] is False
    assert malformed["official_verification_status"] == "NEEDS_MANUAL_REVIEW"
    assert ambiguous["normalized_number"] is None
    assert ambiguous["official_verification_status"] == "NEEDS_MANUAL_REVIEW"


def test_declaration_detection_preserves_evidence_and_conditional_applicability():
    text = (
        "Name of Food: Savoury snack\n"
        "Ingredients: oats, wheat flour, compound seasoning (salt, cumin)\n"
        "FSSAI License No: 12345678901234\n"
        "Net Quantity: 100 g\n"
        "Packed by: Example Foods Pvt Ltd\n"
        "Consumer Care: help@example.in\n"
        "Batch No: A123\n"
        "Store in a cool, dry place"
    )
    report = analyze_label_compliance(text, product_category="frozen foods")
    fields = {item["field_name"]: item for item in report["mandatory_declarations"]}
    rules = {item["rule_id"]: item for item in report["regulatory_rules"]}

    assert fields["name_of_food"]["extracted_value"] == "Savoury snack"
    assert fields["ingredient_list"]["validation_status"] == "PASS"
    assert fields["net_quantity"]["detected"] is True
    assert fields["manufacturer_details"]["detected"] is True
    assert fields["consumer_care_information"]["detected"] is True
    assert fields["batch_or_lot"]["detected"] is True
    assert fields["storage_instructions"]["detected"] is True
    assert rules["label-storage"]["result_classification"] == "PASS"
    assert rules["label-storage"]["applicability_status"] == "NEEDS_MANUAL_REVIEW"
    assert report["legal_compliance_determination"] == "NOT_EVALUATED"
    assert report["source_text"] == text


def test_storage_rule_is_not_applicable_outside_its_configured_categories():
    report = analyze_label_compliance(
        "Ingredients: wheat flour",
        product_category="biscuits",
    )
    storage_rule = next(
        item for item in report["regulatory_rules"] if item["rule_id"] == "label-storage"
    )

    assert storage_rule["result_classification"] == "NOT_APPLICABLE"
    assert storage_rule["applicability_status"] == "NOT_APPLICABLE"


def test_ingredient_and_allergen_evidence_is_distinguished():
    report = analyze_label_compliance(
        "Ingredients: wheat flour, soy lecithin, INS 330, compound seasoning (salt, cumin)\n"
        "May contain traces of peanuts"
    )

    ingredients = report["ingredient_inspection"]
    allergens = report["allergen_inspection"]
    assert ingredients["readable"] is True
    assert "compound seasoning (salt, cumin)" in ingredients["compound_ingredients"]
    assert "INS 330" in ingredients["additive_identifiers"]
    assert allergens["explicit_allergen_declarations"] == []
    assert allergens["may_contain_declarations"][0]["evidence_type"] == "MAY_CONTAIN_STATEMENT"
    assert allergens["ingredient_text_matches"]
    assert all(
        item["evidence_type"] == "POSSIBLE_OCR_DERIVED_MATCH"
        for item in allergens["ingredient_text_matches"]
    )
    assert allergens["confirmed_ingredient_presence"] == []
    assert allergens["safety_conclusion"] == "NOT_EVALUATED"


def test_nutrition_inspection_flags_only_defensible_contradictions():
    report = analyze_label_compliance(
        "Per 100 g\n"
        "Total Sugars 4 g\n"
        "Added Sugars 5 g\n"
        "Total Fat 3 g\n"
        "Saturated Fat 4 g\n"
        "Dietary Fibre 2 g\n"
        "Sodium 200 mg"
    )
    nutrition = report["nutrition_inspection"]
    nutrients = {item["nutrient"]: item for item in nutrition["nutrients"]}

    assert nutrition["basis"] == "per_100g"
    assert nutrients["fiber_g"]["value"] == 2
    assert len(nutrition["inconsistencies"]) == 2
    assert all(
        item["classification"] == "POTENTIAL_ISSUE"
        for item in nutrition["inconsistencies"]
    )
    assert "not a regulatory validation" in nutrients["fiber_g"]["explanation"]


def test_ambiguous_and_conflicting_nutrition_values_need_review():
    report = analyze_label_compliance(
        "Total Sugars 4 g\nTotal Sugars 5 g\nSodium: --"
    )
    nutrients = {item["nutrient"]: item for item in report["nutrition_inspection"]["nutrients"]}

    assert nutrients["sugar_g"]["value"] is None
    assert nutrients["sugar_g"]["classification"] == "NEEDS_MANUAL_REVIEW"
    assert nutrients["sodium_mg"]["classification"] == "NEEDS_MANUAL_REVIEW"


def test_dates_support_indian_day_first_and_month_year_without_inference():
    report = analyze_label_compliance(
        "Mfg Date: 31/12/2025\nBest Before: 11/2027\nUse By: 01/02/2025",
        as_of_date=date(2026, 1, 1),
    )
    dates = {item["date_type"]: item for item in report["date_inspection"]["dates"]}

    assert dates["manufacturing_date"]["normalized_date"] == "2025-12-31"
    assert dates["best_before"]["normalized_date"] == "2027-11"
    assert dates["best_before"]["classification"] == "PASS"
    assert dates["expiry_date"]["normalized_date"] is None
    assert dates["expiry_date"]["classification"] == "NEEDS_MANUAL_REVIEW"
    assert report["date_inspection"]["shelf_life_inferred"] is False


def test_expiry_and_impossible_dates_are_not_silently_accepted():
    expired = analyze_label_compliance(
        "Expiry Date: 31/12/2025",
        as_of_date=date(2026, 1, 1),
    )
    impossible = analyze_label_compliance(
        "Mfg Date: 31/02/2025",
        as_of_date=date(2026, 1, 1),
    )

    assert expired["date_inspection"]["dates"][0]["classification"] == "POTENTIAL_ISSUE"
    assert impossible["date_inspection"]["dates"][0]["classification"] == "NEEDS_MANUAL_REVIEW"


def test_vegetarian_text_detection_never_claims_image_symbol_verification():
    text_report = analyze_label_compliance("Green dot indicates vegetarian food")
    conflict_report = analyze_label_compliance(
        "Vegetarian product\nNon-vegetarian product"
    )

    assert text_report["vegetarian_declaration"]["declaration"] == "VEGETARIAN"
    assert text_report["vegetarian_declaration"]["symbol_image_inspected"] is False
    assert text_report["vegetarian_declaration"]["symbol_verification_status"] == "NOT_EVALUATED"
    assert conflict_report["vegetarian_declaration"]["status"] == "POTENTIAL_ISSUE"


def test_visual_symbol_candidate_remains_separate_and_requires_manual_review():
    report = analyze_label_compliance(
        "Ingredients: oats",
        extraction_metadata={
            "symbol_detection": {
                "image_inspected": True,
                "vegetarian": {"status": "DETECTED"},
                "non_vegetarian": {"status": "NOT_DETECTED"},
            }
        },
    )

    vegetarian = report["vegetarian_declaration"]
    assert vegetarian["declaration"] is None
    assert vegetarian["symbol_verification_status"] == "NEEDS_MANUAL_REVIEW"
    assert any(
        item["field"] == "vegetarian_symbol"
        for item in report["manual_review_requirements"]
    )


def test_empty_or_incomplete_ocr_never_becomes_a_legal_compliance_result():
    report = analyze_label_compliance("")

    assert report["overall_status"] == "NOT_EVALUATED"
    assert report["legal_compliance_determination"] == "NOT_EVALUATED"
    assert report["fssai_license_information"]["official_verification_status"] == "NEEDS_MANUAL_REVIEW"
    assert any("not proof" in item.lower() for item in report["ocr_limitations"])


def test_compliance_api_and_product_analysis_return_the_unified_report():
    text = (
        "Name of Food: Oat snack\n"
        "Ingredients: oats, honey\n"
        "FSSAI License No: 12345678901234"
    )
    response = client.post(
        "/analyze/label-compliance",
        json={"label_text": text, "product_category": "snack"},
    )
    product_response = client.post(
        "/analyze/product",
        json={
            "product_name": "Reviewed oat snack",
            "label_text": text,
            "label_corrections": {"product_name": "Reviewed oat snack"},
            "corrections_confirmed": True,
            "extraction_metadata": {
                "fields": [
                    {
                        "field_name": "product_name",
                        "confidence_state": "MEDIUM_CONFIDENCE",
                    }
                ],
                "symbol_detection": {"image_inspected": True},
            },
            "symbol_review": "VEGETARIAN",
        },
    )

    assert response.status_code == 200
    assert response.json()["fssai_license_information"]["official_verification_status"] == "NOT_VERIFIED"
    assert response.json()["regulatory_sources"]
    assert product_response.status_code == 200
    assert product_response.json()["compliance_report"]["product_information"]["product_name"] == "Reviewed oat snack"
    assert product_response.json()["compliance_report"]["source_text"] == text
    assert product_response.json()["compliance_report"]["corrections_applied"] is True
    assert product_response.json()["compliance_report"]["vegetarian_declaration"]["symbol_verification_status"] == "USER_CONFIRMED"


def test_extraction_api_includes_compliance_report(monkeypatch):
    from app.services import label_ocr

    monkeypatch.setattr(label_ocr, "validate_image", lambda _image: None)
    monkeypatch.setattr(
        label_ocr,
        "extract_image_data",
        lambda _image: {
            "ocr_text": "Ingredients: oats\nFSSAI License No: 12345678901234",
            "raw_ocr_text": "Ingredients: oats\nFSSAI License No: 12345678901234",
            "regions": [],
            "fields": [],
            "symbol_detection": {"image_inspected": True},
            "processing": {"original_image_unchanged": True},
            "ocr_quality": {"mean_word_confidence": None},
            "ocr_passes": [],
        },
    )
    response = client.post(
        "/extract/label",
        files={"file": ("label.png", b"image bytes", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["compliance_report"]["legal_compliance_determination"] == "NOT_EVALUATED"


def test_unconfirmed_corrections_are_not_used_as_analysis_evidence():
    report = analyze_label_compliance(
        "Product Name: Original bar\nIngredients: oats, honey\nTotal Sugars 4 g",
        label_corrections={
            "product_name": "Corrected bar",
            "ingredients_text": "milk powder, sugar",
            "nutrients": {"sugar_g": 8},
        },
        corrections_confirmed=False,
    )

    assert report["product_information"]["product_name"] == "Original bar"
    assert report["ingredient_inspection"]["final_text"] == "oats, honey"
    assert next(
        item
        for item in report["nutrition_inspection"]["nutrients"]
        if item["nutrient"] == "sugar_g"
    )["value"] == 4
    assert report["corrections_applied"] is False
    assert report["user_corrections"]["values"] == {}


def test_confirmed_corrections_override_analysis_but_keep_original_ocr():
    source = (
        "Product Name: Original bar\n"
        "Ingredients: oats, honey\n"
        "Total Sugars 4 g\n"
        "FSSAI License No: 12345"
    )
    report = analyze_label_compliance(
        source,
        label_corrections={
            "product_name": "Reviewed bar",
            "ingredients_text": "milk powder, sugar",
            "nutrients": {"sugar_g": 8},
            "other_fields": {
                "fssai_license_number": "12345678901234",
                "manufacturing_date": "31/12/2025",
            },
        },
        corrections_confirmed=True,
        extraction_metadata={
            "fields": [
                {
                    "field_name": "nutrients.sugar_g",
                    "confidence_state": "LOW_CONFIDENCE",
                    "source_text": "Total Sugars 4 g",
                }
            ],
            "symbol_detection": {
                "image_inspected": True,
                "vegetarian": {"status": "DETECTED"},
                "non_vegetarian": {"status": "NOT_DETECTED"},
            },
        },
        symbol_review="VEGETARIAN",
    )

    assert report["product_information"]["product_name"] == "Reviewed bar"
    assert report["product_information"]["original_ocr_value"] == "Original bar"
    assert report["ingredient_inspection"]["original_text"] == "oats, honey"
    assert report["ingredient_inspection"]["final_text"] == "milk powder, sugar"
    assert next(
        item
        for item in report["nutrition_inspection"]["nutrients"]
        if item["nutrient"] == "sugar_g"
    )["value"] == 8
    assert report["fssai_license_information"]["format_valid"] is True
    assert report["fssai_license_information"]["official_verification_status"] == "NOT_VERIFIED"
    assert report["fssai_license_information"]["correction_applied"] is True
    assert report["fssai_license_information"]["original_ocr_number"] == "12345"
    assert report["date_inspection"]["dates"][-1]["correction_applied"] is True
    assert report["date_inspection"]["original_ocr_dates"] == []
    assert report["vegetarian_declaration"]["symbol_image_inspected"] is True
    assert report["vegetarian_declaration"]["symbol_verification_status"] == "USER_CONFIRMED"
    assert report["vegetarian_declaration"]["declaration"] is None
    assert report["source_text"] == source
    assert report["original_ocr_text"] == source
    assert report["corrections_applied"] is True
    assert any(item["field"] == "nutrients.sugar_g" for item in report["manual_review_requirements"])


def test_compliance_api_uses_only_confirmed_corrections_and_validates_metadata():
    source = "Product Name: Original bar\nIngredients: oats"
    response = client.post(
        "/analyze/label-compliance",
        json={
            "label_text": source,
            "label_corrections": {"product_name": "Reviewed bar"},
            "corrections_confirmed": True,
        },
    )
    invalid_response = client.post(
        "/analyze/label-compliance",
        content=json.dumps(
            {
                "label_text": source,
                "extraction_metadata": {"large": "x" * 50_001},
            }
        ),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["product_information"]["product_name"] == "Reviewed bar"
    assert response.json()["source_text"] == source
    assert invalid_response.status_code == 422

