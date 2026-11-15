import pytest

from app.services.ingredient_analysis import analyze_ingredients


@pytest.mark.parametrize(
    ("label_text", "canonical_name"),
    [
        ("Rice grits", "Rice grits"),
        ("Potato flakes", "Potato flakes"),
        ("Corn grits", "Corn grits"),
        (
            "Edible vegetable oil (corn/soybean oil)",
            "Edible vegetable oil",
        ),
        ("Iodized salt", "Iodized salt"),
        ("Sugar", "Sugar"),
        ("INS 170(i)", "Calcium carbonate"),
        ("INS 551", "Silicon dioxide"),
        ("Chilli powder", "Chilli powder"),
        ("Black pepper powder", "Black pepper powder"),
        ("Garlic and onion powder", "Garlic and onion powder"),
        ("INS 260", "Acetic acid"),
        ("INS 330", "Citric acid"),
        ("INS 296", "Malic acid"),
        (
            "Natural and nature-identical flavouring substances",
            "Natural and nature-identical flavouring substances",
        ),
        ("Tamarind powder", "Tamarind powder"),
        ("INS 627", "Disodium guanylate"),
        ("INS 631", "Disodium inosinate"),
        ("Spice extract", "Spice extract"),
        ("INS 160c(i)", "Paprika extract"),
    ],
)
def test_curated_ingredients_and_additive_codes_are_recognized(
    label_text, canonical_name
):
    result = analyze_ingredients([label_text], ingredients_available=True)
    ingredient = result["ingredients"][0]

    assert ingredient["matched_name"] == canonical_name
    assert ingredient["normalized_name"] == canonical_name
    assert ingredient["recognition_status"] == "Recognized"
    assert ingredient["original_label_text"] == label_text
    assert ingredient["function"]


@pytest.mark.parametrize(
    "label_text",
    [
        "ins 330",
        "INS330",
        "E330",
        "  CITRIC---ACID ",
        "natural and nature identical flavoring substances",
        "CHILLI   powder",
        "garlic & onion powder",
        "edible vegetable oil (corn/soybean oil)",
    ],
)
def test_matching_normalizes_case_spacing_punctuation_and_verified_aliases(
    label_text,
):
    result = analyze_ingredients([label_text], ingredients_available=True)
    assert result["ingredients"][0]["recognition_status"] == "Recognized"


def test_nested_ingredients_and_multiple_additives_are_expanded_exactly():
    result = analyze_ingredients(
        ["Seasoning (INS 627, INS 631, black pepper powder)"],
        ingredients_available=True,
    )

    items = result["ingredients"]
    assert [item["ingredient"] for item in items] == [
        "Seasoning",
        "INS 627",
        "INS 631",
        "black pepper powder",
    ]
    assert [item["matched_name"] for item in items] == [
        None,
        "Disodium guanylate",
        "Disodium inosinate",
        "Black pepper powder",
    ]
    assert items[0]["needs_review"] is True
    assert all(item["recognition_status"] == "Recognized" for item in items[1:])
    assert result["needs_review"] is True


def test_single_nested_ingredient_is_recognized_without_fuzzy_matching():
    result = analyze_ingredients(
        ["Seasoning (INS 330)"],
        ingredients_available=True,
    )

    assert [item["matched_name"] for item in result["ingredients"]] == [
        None,
        "Citric acid",
    ]


def test_unrecognized_ocr_text_is_not_fuzzy_matched():
    result = analyze_ingredients(["potasium sorbate"], ingredients_available=True)
    ingredient = result["ingredients"][0]

    assert ingredient["matched_name"] is None
    assert ingredient["recognition_status"] == "Unrecognized or uncertain"
    assert ingredient["needs_review"] is True
    assert "not classified as harmful" in ingredient["explanation"]


def test_recognized_additive_is_not_claimed_harmful_or_proven_safe():
    result = analyze_ingredients(["INS 551"], ingredients_available=True)
    ingredient = result["ingredients"][0]

    assert ingredient["verification_status"] == "UNVERIFIED"
    assert ingredient["concern_status"] == "unknown"
    assert "does not establish a health conclusion" in ingredient["explanation"]
    assert ingredient["source_url"] is None


def test_existing_verified_sources_are_retained():
    result = analyze_ingredients(
        ["Peanut", "Citric acid"],
        ingredients_available=True,
    )

    peanut, citric_acid = result["ingredients"]
    assert peanut["evidence_source"] == "U.S. FDA, Food Allergies"
    assert peanut["source_url"].startswith("https://www.fda.gov/")
    assert "peanut allergy" in peanut["explanation"]
    assert citric_acid["verification_status"] == "REVIEW_REQUIRED"
    assert citric_acid["source_url"] is None
    assert citric_acid["source_references"]
    assert all(
        not source["verified"] for source in citric_acid["source_references"]
    )


def test_only_source_backed_health_concerns_are_returned_for_display():
    result = analyze_ingredients(
        [
            "Peanut",
            "Sugar",
            "Citric acid",
            "Silicon dioxide",
            "potasium sorbate",
        ],
        ingredients_available=True,
    )

    assert result["evidence_concern_count"] == 1
    assert [item["matched_name"] for item in result["evidence_concerns"]] == [
        "Peanut"
    ]
    concern = result["evidence_concerns"][0]
    assert concern["concern_status"] == "evidence_based"
    assert concern["evidence_source"]
    assert concern["source_url"].startswith("https://")
    assert concern["explanation"]
    assert concern["evidence_context"]


def test_no_concern_and_unknown_items_are_excluded_from_display_concerns():
    result = analyze_ingredients(
        ["Sugar", "INS 551", "potasium sorbate"],
        ingredients_available=True,
    )

    assert result["evidence_concern_count"] == 0
    assert result["evidence_concerns"] == []


def test_missing_ingredient_list_remains_unavailable():
    result = analyze_ingredients(None, ingredients_available=False)

    assert result["status"] == "Unavailable"
    assert result["needs_review"] is True
    assert result["ingredients"] == []
    assert result["evidence_concerns"] == []
    assert result["evidence_concern_count"] == 0


@pytest.mark.parametrize(
    ("label_text", "canonical_name"),
    [
        ("E211", "Sodium benzoate"),
        ("E-202", "Potassium sorbate"),
        ("INS 330", "Citric acid"),
        ("621", "Monosodium glutamate"),
        ("E 951", "Aspartame"),
        ("INS-955", "Sucralose"),
        ("MSG", "Monosodium glutamate"),
    ],
)
def test_initial_additives_match_identifiers_and_common_aliases(
    label_text,
    canonical_name,
):
    result = analyze_ingredients([label_text], ingredients_available=True)

    assert result["ingredients"][0]["canonical_name"] == canonical_name
    assert result["ingredients"][0]["match_quality"] == "exact"


@pytest.mark.parametrize("label_text", ["X211", "E2110", "batch621", "621mg"])
def test_additive_identifiers_do_not_match_embedded_text(label_text):
    result = analyze_ingredients([label_text], ingredients_available=True)

    assert result["ingredients"][0]["canonical_name"] is None
