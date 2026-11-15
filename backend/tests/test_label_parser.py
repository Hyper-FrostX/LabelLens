import pytest

from app.services.label_parser import parse_label_text


def test_parser_extracts_explicit_label_fields_and_nested_ingredients():
    text = "\n".join(
        [
            "Product Name: Oat Crunch",
            "Per Serving",
            "Serving Size: 30 g",
            "Total Sugars 8.5 g",
            "Sodium 120 mg",
            "Saturated Fat 1.5 g",
            "Ingredients: oats, spices (cinnamon, nutmeg), honey",
            "Contains: wheat",
        ]
    )

    result = parse_label_text(text)

    assert result["product_name"]["value"] == "Oat Crunch"
    assert result["basis"] == "per_serving"
    assert result["serving_size_text"] == "30 g"
    assert result["nutrients"]["sugar_g"]["value"] == 8.5
    assert result["nutrients"]["sugar_g"]["unit"] == "g"
    assert result["nutrients"]["sodium_mg"]["value"] == 120
    assert result["nutrients"]["saturated_fat_g"]["value"] == 1.5
    assert result["ingredients_text"] == (
        "oats, spices (cinnamon, nutmeg), honey"
    )
    assert result["ingredients"] == [
        "oats",
        "spices (cinnamon, nutmeg)",
        "honey",
    ]
    assert result["ocr_text"] == text


def test_parser_does_not_guess_ambiguous_basis_or_incomplete_values():
    result = parse_label_text(
        "Per serving and per 100 g\n"
        "Total Sugars 4 g 8 g\n"
        "Ingredients: oats (spices, cinnamon"
    )

    assert result["basis"] is None
    assert result["nutrients"]["sugar_g"]["value"] is None
    assert result["ingredients_text"] == "oats (spices, cinnamon"
    assert result["ingredients"] is None
    assert "basis" in result["review_required_fields"]
    assert "sugar_g" in result["review_required_fields"]
    assert "ingredients" in result["review_required_fields"]


def test_parser_marks_all_extracted_nutrients_for_review_without_confidence():
    result = parse_label_text(
        "Per 100 g\n"
        "Total Sugars 4 g\n"
        "Sodium 80 mg\n"
        "Saturated Fat 1 g\n"
        "Serving Size: 100 g\n"
        "Ingredients: oats"
    )

    for nutrient in result["nutrients"].values():
        assert nutrient["confidence"] is None
        assert nutrient["needs_review"] is True
    assert result["review_required_fields"] == [
        "product_name",
        "basis",
        "serving_size_text",
        "sugar_g",
        "added_sugar_g",
        "sodium_mg",
        "saturated_fat_g",
        "energy_kcal",
        "energy_kj",
        "total_fat_g",
        "trans_fat_g",
        "carbohydrates_g",
        "protein_g",
        "salt_g",
        "ingredients",
        "allergens",
        "may_contain",
        "fssai_license_number",
    ]


def test_parser_extracts_nutrients_from_table_ocr_rows_and_keeps_review_flags():
    result = parse_label_text(
        "Nutrition Facts\n"
        "Amount Per Serving\n"
        "Serving Size: 25 g\n"
        "Saturated Fat 0.8 g 4%\n"
        "Sodium 249 mg 11%\n"
        "Total Sugars 3.4 g 3%\n"
        "Added Sugars 1.5 g 2%\n"
        "Protein 2 g\n"
        "Total Carbohydrates 16.9 g\n"
        "Ingredients: corn, oil, seasoning"
    )

    assert result["basis"] == "per_serving"
    assert result["serving_size_text"] == "25 g"
    assert result["nutrients"]["saturated_fat_g"]["value"] == 0.8
    assert result["nutrients"]["sodium_mg"]["value"] == 249
    assert result["nutrients"]["sugar_g"]["value"] == 3.4
    assert result["nutrients"]["saturated_fat_g"]["needs_review"] is True
    assert result["nutrients"]["sodium_mg"]["needs_review"] is True
    assert result["nutrients"]["sugar_g"]["needs_review"] is True
    assert all(
        result["nutrients"][field]["confidence"] is None
        for field in ("saturated_fat_g", "sodium_mg", "sugar_g")
    )
    assert all(
        field in result["review_required_fields"]
        for field in ("saturated_fat_g", "sodium_mg", "sugar_g")
    )


def test_parser_extracts_values_from_reported_packet_ocr_text():
    result = parse_label_text(
        "Serving Size 25g Amount %\n"
        "Servings Per Container 2.5 Per Serve RDA*\n"
        "Saturated Fat (g) 0.8 4%\n"
        "Sodium (mg) 249 12%\n"
        "Total Sugar (g) 3.4\n"
        "Added Sugar (g) 1.5 3%"
    )

    assert result["serving_size_text"] == "25 g"
    assert result["nutrients"]["sugar_g"]["value"] == 3.4
    assert result["nutrients"]["sodium_mg"]["value"] == 249
    assert result["nutrients"]["saturated_fat_g"]["value"] == 0.8
    assert result["nutrients"]["sugar_g"]["source_text"] == "Total Sugar (g) 3.4"
    assert result["nutrients"]["added_sugar_g"]["source_text"] == (
        "Added Sugar (g) 1.5 3%"
    )
    assert result["nutrients"]["sodium_mg"]["source_text"] == (
        "Sodium (mg) 249 12%"
    )
    assert result["nutrients"]["saturated_fat_g"]["source_text"] == (
        "Saturated Fat (g) 0.8 4%"
    )
    assert all(
        result["nutrients"][field]["confidence"] is None
        and result["nutrients"][field]["needs_review"] is True
        for field in ("sugar_g", "sodium_mg", "saturated_fat_g")
    )


def test_parser_handles_wrapped_nutrient_rows_and_optional_rda_percentages():
    result = parse_label_text(
        "Serving Size: 25 g\n"
        "Saturated Fat (g)\n0.8\n"
        "Sodium (mg) 249\n"
        "Total Sugar (g) 3.4 3%"
    )

    assert result["nutrients"]["saturated_fat_g"]["value"] == 0.8
    assert result["nutrients"]["sodium_mg"]["value"] == 249
    assert result["nutrients"]["sugar_g"]["value"] == 3.4


def test_parser_does_not_confuse_added_sugar_or_total_fat_with_target_fields():
    result = parse_label_text(
        "Added Sugar (g) 1.5 3%\n"
        "Total Fat (g) 4.2 6%\n"
        "Sodium (mg) 249"
    )

    assert result["nutrients"]["sugar_g"]["value"] is None
    assert result["nutrients"]["added_sugar_g"]["value"] == 1.5
    assert result["nutrients"]["saturated_fat_g"]["value"] is None
    assert result["nutrients"]["sodium_mg"]["value"] == 249
    assert "sugar_g" in result["review_required_fields"]
    assert "saturated_fat_g" in result["review_required_fields"]


def test_parser_does_not_treat_ingredient_names_as_nutrient_rows():
    result = parse_label_text(
        "Sodium chloride 200 mg\n"
        "Fatty acid 3 g\n"
        "Sugar alcohol 5 g"
    )

    assert result["nutrients"]["sodium_mg"]["value"] is None
    assert result["nutrients"]["total_fat_g"]["value"] is None
    assert result["nutrients"]["sugar_g"]["value"] is None


def test_parser_keeps_duplicate_or_wrong_unit_values_unresolved():
    result = parse_label_text(
        "Total Sugar (g) 3.4\n"
        "Total Sugars 4 g\n"
        "Sodium (g) 249\n"
        "Saturated Fat (mg) 0.8"
    )

    assert result["nutrients"]["sugar_g"]["value"] is None
    assert result["nutrients"]["sodium_mg"]["value"] is None
    assert result["nutrients"]["saturated_fat_g"]["value"] is None


def test_parser_handles_thousands_separators_without_truncating_values():
    result = parse_label_text("Sodium 1,200 mg\nTotal Fat 1,200 g")

    assert result["nutrients"]["sodium_mg"]["value"] == 1200
    assert result["nutrients"]["total_fat_g"]["value"] == 1200


def test_parser_distinguishes_added_sugar_and_supports_per_100_ml():
    result = parse_label_text(
        "Per 100 ml\n"
        "Total Sugars (g) 8\n"
        "Added Sugars (g) 4\n"
        "Sodium (mg) 80\n"
        "Saturated Fat (g) 1"
    )

    assert result["basis"] == "per_100ml"
    assert result["nutrients"]["sugar_g"]["value"] == 8
    assert result["nutrients"]["added_sugar_g"]["value"] == 4
    assert result["nutrients"]["sodium_mg"]["unit"] == "mg"
    assert result["nutrients"]["saturated_fat_g"]["unit"] == "g"


def test_parser_leaves_ambiguous_basis_and_wrong_added_sugar_unit_unresolved():
    result = parse_label_text(
        "Per 100 g\n"
        "Per 100 ml\n"
        "Added Sugar (mg) 25"
    )

    assert result["basis"] is None
    assert result["nutrients"]["added_sugar_g"]["value"] is None
    assert result["nutrients"]["added_sugar_g"]["unit"] is None


def test_parser_does_not_treat_salt_as_sodium():
    result = parse_label_text("Per 100 g\nSalt 1 g")

    assert result["nutrients"]["sodium_mg"]["value"] is None


def test_parser_recognizes_per_serve_and_supplied_snack_label_values():
    result = parse_label_text(
        "Serving Size 25g Amount %\n"
        "Amount: Per Serve\n"
        "Total Sugar (g) 3.4\n"
        "Added Sugar (g) 1.5\n"
        "Sodium (mg) 249\n"
        "Saturated Fat (g) 0.8"
    )

    assert result["basis"] == "per_serving"
    assert result["serving_size_text"] == "25 g"
    assert result["nutrients"]["sugar_g"]["value"] == 3.4
    assert result["nutrients"]["added_sugar_g"]["value"] == 1.5
    assert result["nutrients"]["sodium_mg"]["value"] == 249
    assert result["nutrients"]["saturated_fat_g"]["value"] == 0.8


def test_parser_does_not_infer_per_serve_from_serving_size_alone():
    result = parse_label_text("Serving Size 25 g\nTotal Sugar (g) 3.4")

    assert result["basis"] is None


def test_parser_extracts_indian_label_nutrients_and_keeps_salt_separate():
    result = parse_label_text(
        "Per 100 g\n"
        "Energy 1800 kJ / 430 kcal\n"
        "Total Fat (g) 15\n"
        "Saturated Fat (g) 3.2\n"
        "Trans Fat (g) 0\n"
        "Carbohydrate (g) 62\n"
        "Total Sugars (g) 18\n"
        "Added Sugars (g) 10\n"
        "Protein (g) 8\n"
        "Sodium (mg) 450\n"
        "Salt 1.1 g"
    )

    nutrients = result["nutrients"]
    assert result["basis"] == "per_100g"
    assert nutrients["energy_kj"]["value"] == 1800
    assert nutrients["energy_kcal"]["value"] == 430
    assert nutrients["total_fat_g"]["value"] == 15
    assert nutrients["saturated_fat_g"]["value"] == 3.2
    assert nutrients["trans_fat_g"]["value"] == 0
    assert nutrients["carbohydrates_g"]["value"] == 62
    assert nutrients["sugar_g"]["value"] == 18
    assert nutrients["added_sugar_g"]["value"] == 10
    assert nutrients["protein_g"]["value"] == 8
    assert nutrients["sodium_mg"]["value"] == 450
    assert nutrients["salt_g"]["value"] == 1.1
    assert nutrients["sodium_mg"]["unit"] == "mg"
    assert nutrients["salt_g"]["unit"] == "g"


@pytest.mark.parametrize(
    ("text", "expected_value", "expected_unit"),
    [
        ("Serving Size: 25g", "25 g", "g"),
        ("Serving Size: 200 ml", "200 ml", "ml"),
        ("Serving Size: 2 pieces", "2 pieces", "piece"),
        ("Serving Size: 1 cup (240 ml)", "1 cup (240 ml)", "cup"),
    ],
)
def test_parser_preserves_different_serving_size_units(
    text,
    expected_value,
    expected_unit,
):
    result = parse_label_text(text)

    assert result["serving_size_text"] == expected_value
    assert result["extracted_fields"]["serving_size_text"]["unit"] == expected_unit
    assert result["extracted_fields"]["serving_size_text"]["source_text"] == text


def test_parser_extracts_allergen_and_may_contain_declarations():
    result = parse_label_text(
        "Ingredients: oats, spice mix (cumin, pepper (black))\n"
        "Allergen Advice: Contains wheat, soy; may contain traces of nuts"
    )

    assert result["allergens"]["value"] == ["wheat", "soy"]
    assert result["may_contain"]["value"] == ["nuts"]
    assert result["allergens"]["source_text"].startswith("Allergen Advice:")
    assert result["may_contain"]["source_text"].startswith("Allergen Advice:")
    assert result["ingredients"] == [
        "oats",
        "spice mix (cumin, pepper (black))",
    ]


@pytest.mark.parametrize(
    "line",
    [
        "FSSAI License No: 12345678901234",
        "FSSAI Lic. No. 1234 5678 9012 34",
    ],
)
def test_parser_extracts_fssai_license_number_and_source(line):
    result = parse_label_text(line)

    assert result["fssai_license_number"]["value"] == "12345678901234"
    assert result["fssai_license_number"]["source_text"] == line
    assert result["fssai_license_number"]["needs_review"] is True
    assert result["fssai_license_number"]["confidence"] is None


def test_parser_extracts_fssai_license_number_wrapped_onto_next_line():
    text = "FSSAI License No:\n12345678901234"
    result = parse_label_text(text)

    assert result["fssai_license_number"]["value"] == "12345678901234"
    assert result["fssai_license_number"]["source_text"] == text


def test_parser_leaves_missing_and_ambiguous_values_for_manual_review():
    result = parse_label_text(
        "Energy 200\n"
        "Sodium: --\n"
        "Total Sugar 4 g / 5 g\n"
        "FSSAI License No: 12345"
    )

    assert result["nutrients"]["energy_kcal"]["value"] is None
    assert result["nutrients"]["sodium_mg"]["value"] is None
    assert result["nutrients"]["sugar_g"]["value"] is None
    assert result["fssai_license_number"]["value"] is None
    assert result["nutrients"]["sugar_g"]["source_text"] == (
        "Total Sugar 4 g / 5 g"
    )


def test_parser_extracts_calories_without_guessing_other_missing_units():
    result = parse_label_text(
        "Calories 120\n"
        "Energy 500\n"
        "Total Fat 3"
    )

    assert result["nutrients"]["energy_kcal"]["value"] == 120
    assert result["nutrients"]["energy_kcal"]["unit"] == "kcal"
    assert result["nutrients"]["energy_kcal"]["source_text"] == "Calories 120"
    assert result["nutrients"]["energy_kj"]["value"] is None
    assert result["nutrients"]["total_fat_g"]["value"] is None


@pytest.mark.parametrize("text", ["", "Nutrition facts unavailable", "???"])
def test_parser_handles_empty_or_unstructured_ocr_without_inventing_values(text):
    result = parse_label_text(text)

    assert result["product_name"]["value"] is None
    assert result["serving_size_text"] is None
    assert result["basis"] is None
    assert all(field["value"] is None for field in result["nutrients"].values())
    assert result["ingredients"] is None
    assert result["allergens"]["value"] is None
    assert result["may_contain"]["value"] is None
    assert result["fssai_license_number"]["value"] is None
    assert all(
        field["needs_review"]
        for name, field in result["extracted_fields"].items()
        if name != "nutrients"
    )
    assert all(
        field["needs_review"]
        for field in result["extracted_fields"]["nutrients"].values()
    )
