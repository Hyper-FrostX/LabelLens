import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.services.ingredient_allergen_aliases import ALLERGEN_ALIASES
from app.services.ingredient_analysis import analyze_ingredients, match_allergen_text
from app.services.label_parser import parse_label_text, split_ingredients_text

_OCR_DIGIT_MAP = {
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "S": "5",
    "B": "8",
    "G": "6",
    "Z": "2",
    "T": "7",
}
_NO_LICENSE_LOOKUP = "No official verification API configured; no lookup performed."
_LICENSE_TOKEN = re.compile(
    r"(?<![A-Z0-9])([0-9OQILSBGZT](?:[ \t\n-]*[0-9OQILSBGZT]){0,17})(?![A-Z0-9])",
    re.IGNORECASE,
)
_LICENSE_LABEL = re.compile(r"\bfssai\b", re.IGNORECASE)
_DATE_TOKEN = re.compile(
    r"(?<!\d)(?:"
    r"\d{4}[./-]\d{1,2}[./-]\d{1,2}|"
    r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
    r"\d{1,2}[./-]\d{4}|"
    r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|"
    r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|"
    r"[A-Za-z]{3,9}\s+\d{4}"
    r")(?!\d)",
    re.IGNORECASE,
)
_MONTH_NAMES = {
    name.casefold(): index
    for index, name in enumerate(
        (
            "",
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        )
    )
    if name
}
_MONTH_NAMES.update(
    {name[:3].casefold(): number for name, number in _MONTH_NAMES.items() if len(name) > 3}
)

REGULATORY_SOURCES = (
    {
        "id": "fssai_labelling_2020",
        "title": "Food Safety and Standards (Labelling and Display) Regulations, 2020",
        "issuing_authority": "Food Safety and Standards Authority of India",
        "publication_date": "2020-11-17",
        "provisions": "General labelling provisions; category and exemption review is required.",
        "source_url": (
            "https://www.fssai.gov.in/docs/food-law/regulations/"
            "5fd87c6a0f6adGazette_Notification_Labelling_Display_14_12_2020.pdf"
        ),
        "source_version": "Original Gazette notification; later amendments exist.",
        "verification_status": "REVIEW_REQUIRED",
        "last_reviewed_date": "2026-11-16",
    },
    {
        "id": "fssai_labelling_compendium_viii",
        "title": "FSSAI Labelling and Display Regulations, Version VIII",
        "issuing_authority": "Food Safety and Standards Authority of India",
        "publication_date": "2025-09-09",
        "provisions": "Consolidated reference; not treated as a substitute for subsequent notifications.",
        "source_url": (
            "https://www.fssai.gov.in/docs/food-law/regulations/"
            "Comp_Labelling%20Display_Version%20VIII_09_09_2025.pdf"
        ),
        "source_version": "Version VIII, 2025-09-09",
        "verification_status": "REVIEW_REQUIRED",
        "last_reviewed_date": "2026-11-16",
    },
    {
        "id": "fssai_allergens_reg_5_14",
        "title": "FSSAI Labelling and Display Regulations, 2020, Regulation 5(14), as amended",
        "issuing_authority": "Food Safety and Standards Authority of India",
        "publication_date": "2020-11-17",
        "provisions": (
            "Regulation 5(14); listed allergen declarations have exceptions "
            "and depend on formulation and product context."
        ),
        "source_url": (
            "https://www.fssai.gov.in/docs/food-law/regulations/"
            "Comp_Labelling%20Display_Version%20VIII_09_09_2025.pdf"
        ),
        "source_version": (
            "Regulation 5(14); 2022 first amendment considered. Later "
            "amendments require category-specific review."
        ),
        "verification_status": "VERIFIED",
        "last_reviewed_date": "2026-11-15",
    },
    {
        "id": "fssai_labelling_amendment_2022",
        "title": "FSSAI Labelling and Display First Amendment Regulations, 2022",
        "issuing_authority": "Food Safety and Standards Authority of India",
        "publication_date": "2022-09-09",
        "provisions": "Amends specified allergen-declaration exceptions.",
        "source_url": (
            "https://www.fssai.gov.in/docs/food-law/regulations/amendments/"
            "labelling-display/Gazette_Notification_FSS_Label_12_09_2022.pdf"
        ),
        "source_version": "Gazette No. 442 (6074 GI/2022)",
        "verification_status": "VERIFIED",
        "last_reviewed_date": "2026-11-15",
    },
    {
        "id": "fssai_labelling_amendment_2026",
        "title": "FSSAI Labelling and Display First Amendment Regulations, 2026",
        "issuing_authority": "Food Safety and Standards Authority of India",
        "publication_date": "2026-03-24",
        "provisions": (
            "Operative clauses amend Regulations 5(3), 8(1), 10, Schedule I "
            "and Schedule II; effective 2027-07-01."
        ),
        "source_url": (
            "https://www.fssai.gov.in/docs/food-law/regulations/amendments/"
            "labelling-display/Notification%20dt%2024_03_2026_NRC.pdf"
        ),
        "source_version": "Effective 2027-07-01",
        "verification_status": "VERIFIED",
        "last_reviewed_date": "2026-11-15",
    },
    {
        "id": "fssai_labelling_milk_logo_2026",
        "title": "FSSAI Labelling and Display Second Amendment Regulations, 2026",
        "issuing_authority": "Food Safety and Standards Authority of India",
        "publication_date": "2026-11-06",
        "provisions": "Inserts a milk and milk products logo requirement effective 2028-07-01.",
        "source_url": (
            "https://www.fssai.gov.in/docs/food-law/regulations/amendments/"
            "labelling-display/FSS(Labelling%20and%20Display)%20-%20Milk%20logo.pdf"
        ),
        "source_version": "Effective 2028-07-01",
        "verification_status": "VERIFIED",
        "last_reviewed_date": "2026-11-15",
    },
    {
        "id": "fssai_official_license_lookup",
        "title": "FSSAI Food Safety Compliance System",
        "issuing_authority": "Food Safety and Standards Authority of India",
        "publication_date": None,
        "provisions": "No official status lookup is performed by this application.",
        "source_url": "https://foscos.fssai.gov.in/",
        "source_version": "No API integration configured",
        "verification_status": "REVIEW_REQUIRED",
        "last_reviewed_date": "2026-11-16",
    },
)
_SOURCES_BY_ID = {source["id"]: source for source in REGULATORY_SOURCES}


@dataclass(frozen=True)
class DetectionRule:
    rule_id: str
    field_name: str
    name: str
    applicability_condition: str
    reference_id: str
    applicable_categories: tuple[str, ...] | None = None


LABEL_DETECTION_RULES = (
    DetectionRule(
        "label-food-name",
        "name_of_food",
        "Food name detection",
        "Label and product category determine the applicable name wording.",
        "fssai_labelling_2020",
    ),
    DetectionRule(
        "label-ingredients",
        "ingredient_list",
        "Ingredient declaration detection",
        "Product type, exemptions, and ingredient formulation affect applicability.",
        "fssai_labelling_2020",
    ),
    DetectionRule(
        "label-nutrition",
        "nutrition_information",
        "Nutrition information detection",
        "Nutrition declarations may have category-specific exemptions or formats.",
        "fssai_labelling_2020",
    ),
    DetectionRule(
        "label-allergens",
        "allergen_declaration",
        "Allergen declaration detection",
        "Depends on ingredients, thresholds, listed allergens, and applicable exceptions.",
        "fssai_allergens_reg_5_14",
    ),
    DetectionRule(
        "label-veg-symbol",
        "vegetarian_declaration",
        "Vegetarian declaration detection",
        "Product formulation and the applicable mark requirements require review.",
        "fssai_labelling_2020",
    ),
    DetectionRule(
        "label-fssai-license",
        "fssai_license_number",
        "FSSAI license or registration number detection",
        "License type and display applicability require product/business context.",
        "fssai_labelling_2020",
    ),
    DetectionRule(
        "label-net-quantity",
        "net_quantity",
        "Net quantity detection",
        "Package type and measurement rules determine the applicable declaration.",
        "fssai_labelling_2020",
    ),
    DetectionRule(
        "label-manufacturer",
        "manufacturer_details",
        "Manufacturer or packer details detection",
        "The responsible business role and package context require review.",
        "fssai_labelling_2020",
    ),
    DetectionRule(
        "label-consumer-care",
        "consumer_care_information",
        "Consumer-care information detection",
        "Applicable package and business details require review.",
        "fssai_labelling_2020",
    ),
    DetectionRule(
        "label-dates",
        "date_markings",
        "Date marking detection",
        "Date type and applicable declaration depend on product category.",
        "fssai_labelling_2020",
    ),
    DetectionRule(
        "label-batch",
        "batch_or_lot",
        "Batch or lot identification detection",
        "Applicable product and package exemptions require review.",
        "fssai_labelling_2020",
    ),
    DetectionRule(
        "label-storage",
        "storage_instructions",
        "Storage instruction detection",
        "Checked for refrigerated or frozen categories; other conditions require review.",
        "fssai_labelling_2020",
        ("refrigerated", "frozen"),
    ),
)

_FIELD_PATTERNS = {
    "net_quantity": re.compile(
        r"\b(?:net\s*(?:qty|quantity|weight|contents?)|quantity)\b"
        r"\s*[:#-]?\s*[\w.,/ -]{1,60}",
        re.IGNORECASE,
    ),
    "manufacturer_details": re.compile(
        r"\b(?:manufactured|manufacture|packed|packaged|marketed|"
        r"imported|distributed)\s+by\b\s*[:#-]?\s*.+",
        re.IGNORECASE,
    ),
    "consumer_care_information": re.compile(
        r"\b(?:consumer|customer)\s*(?:care|complaint|service)|"
        r"\bhelpline\b|\bcontact\s+(?:us|number)\b",
        re.IGNORECASE,
    ),
    "batch_or_lot": re.compile(
        r"\b(?:batch|lot)\s*(?:no\.?|number|code)?\s*[:#-]?\s*\S+",
        re.IGNORECASE,
    ),
    "storage_instructions": re.compile(
        r"\b(?:store|storage|keep|refrigerat|freeze|frozen)\b.{0,140}",
        re.IGNORECASE,
    ),
}
_DATE_LABELS = {
    "manufacturing_date": re.compile(
        r"\b(?:mfg\.?|mfd\.?|manufactur(?:ed|ing)\s+date|date\s+of\s+manufacture)\b",
        re.IGNORECASE,
    ),
    "packing_date": re.compile(
        r"\b(?:pkd\.?|packed\s+on|packing\s+date|date\s+of\s+packing)\b",
        re.IGNORECASE,
    ),
    "best_before": re.compile(r"\bbest\s*[- ]?\s*before\b", re.IGNORECASE),
    "expiry_date": re.compile(
        r"\b(?:exp\.?|expiry|expires?|use\s*[- ]?\s*by)\b",
        re.IGNORECASE,
    ),
}
_VEG_PATTERNS = {
    "non_vegetarian": re.compile(
        r"\b(?:non[\s-]?vegetarian|non[\s-]?veg|contains\s+meat)\b|"
        r"\b(?:red|brown)\s+(?:dot|mark|symbol)\b",
        re.IGNORECASE,
    ),
    "vegetarian": re.compile(
        r"\b(?:vegetarian|veg(?:etarian)?\s+product|suitable\s+for\s+vegetarians?)\b|"
        r"\bgreen\s+(?:dot|mark|symbol)\b",
        re.IGNORECASE,
    ),
}


def _raw_value(field: dict[str, Any] | None) -> Any:
    return field.get("value") if isinstance(field, dict) else None


def _source_value(field: dict[str, Any] | None) -> str | None:
    value = field.get("source_text") if isinstance(field, dict) else None
    return value if isinstance(value, str) and value else None


def _set_reviewed_value(
    parsed: dict[str, Any],
    field_name: str,
    value: Any,
    *,
    unit: str | None = None,
) -> None:
    source = "User-confirmed correction; original OCR is retained separately."
    entry = {
        "value": value,
        "unit": unit,
        "source_text": source,
        "confidence": None,
        "needs_review": False,
    }
    if field_name == "product_name":
        parsed[field_name] = entry
        parsed["extracted_fields"][field_name] = entry
    elif field_name in {"basis", "serving_size_text"}:
        parsed[field_name] = value
        parsed["extracted_fields"][field_name] = entry
    elif field_name == "ingredients_text":
        parsed[field_name] = value
        parsed["ingredients"] = split_ingredients_text(value) if value else None
        parsed["extracted_fields"]["ingredients_text"] = entry
        parsed["extracted_fields"]["ingredients"] = {
            **entry,
            "value": parsed["ingredients"],
        }
    elif field_name in {"allergens", "may_contain"}:
        parsed[field_name] = value
        parsed["extracted_fields"][field_name] = entry
    elif field_name.startswith("nutrients."):
        nutrient_name = field_name.split(".", 1)[1]
        parsed["nutrients"][nutrient_name] = entry
        parsed["extracted_fields"]["nutrients"][nutrient_name] = entry


def _apply_reviewed_corrections(
    parsed: dict[str, Any],
    corrections: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(corrections, dict):
        return {}
    for field_name in (
        "product_name",
        "basis",
        "serving_size_text",
        "ingredients_text",
        "allergens",
        "may_contain",
    ):
        if field_name not in corrections:
            continue
        value = corrections[field_name]
        if field_name in {"product_name", "basis", "serving_size_text", "ingredients_text"}:
            value = value.strip() if isinstance(value, str) else None
        elif isinstance(value, str):
            value = [item.strip() for item in re.split(r"[,;\n]+", value) if item.strip()]
        if field_name in {"allergens", "may_contain"} and value is not None:
            if not isinstance(value, list):
                continue
            value = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        _set_reviewed_value(parsed, field_name, value)

    nutrient_corrections = corrections.get("nutrients")
    if isinstance(nutrient_corrections, dict):
        for nutrient_name, value in nutrient_corrections.items():
            if nutrient_name not in parsed.get("nutrients", {}):
                continue
            unit = parsed["nutrients"][nutrient_name].get("unit")
            try:
                numeric_value = None if value is None or value == "" else float(value)
            except (TypeError, ValueError):
                numeric_value = None
            _set_reviewed_value(
                parsed,
                f"nutrients.{nutrient_name}",
                numeric_value,
                unit=unit,
            )
    other_fields = corrections.get("other_fields")
    return other_fields if isinstance(other_fields, dict) else {}


def _normalize_license_number(value: str) -> str:
    digits = []
    for character in value:
        if character.isdigit():
            digits.append(character)
        elif character.upper() in _OCR_DIGIT_MAP:
            digits.append(_OCR_DIGIT_MAP[character.upper()])
    return "".join(digits)


def _license_candidates(label_text: str) -> list[tuple[str, str]]:
    lines = label_text.splitlines()
    candidates: list[tuple[str, str]] = []
    for index, line in enumerate(lines):
        if not _LICENSE_LABEL.search(line):
            continue
        nearby_text = line
        nearby_source = line
        if index + 1 < len(lines):
            nearby_text = f"{line}\n{lines[index + 1]}"
            nearby_source = nearby_text
        for match in _LICENSE_TOKEN.finditer(nearby_text):
            token = match.group(1).strip()
            normalized = _normalize_license_number(token)
            if normalized:
                candidates.append((token, nearby_source))
    return candidates


def _license_information(
    label_text: str,
    parsed: dict[str, Any],
    *,
    reviewed_number: Any = None,
) -> dict[str, Any]:
    if isinstance(reviewed_number, str) and reviewed_number.strip():
        extracted_number = reviewed_number.strip()
        normalized_number = re.sub(r"[\s-]", "", extracted_number)
        format_valid = bool(re.fullmatch(r"\d{14}", normalized_number))
        return {
            "extracted_number": extracted_number,
            "normalized_number": normalized_number,
            "format_valid": format_valid,
            "official_verification_status": "NOT_VERIFIED" if format_valid else "NEEDS_MANUAL_REVIEW",
            "verification_source": _NO_LICENSE_LOOKUP,
            "confidence": None,
            "explanation": (
                "User-confirmed number matches the 14-digit shape; no official license-status lookup was performed."
                if format_valid
                else "User-confirmed value does not match the 14-digit shape; verify it against the package."
            ),
            "source_text": None,
            "original_ocr_text": label_text,
            "correction_applied": True,
        }
    candidates = _license_candidates(label_text)
    if len(candidates) == 1:
        extracted_number, source_text = candidates[0]
        normalized_number = _normalize_license_number(extracted_number)
        format_valid = bool(re.fullmatch(r"\d{14}", normalized_number))
        corrected_by_ocr = any(character.upper() in _OCR_DIGIT_MAP for character in extracted_number)
        verification_status = (
            "NOT_VERIFIED"
            if format_valid
            else "NEEDS_MANUAL_REVIEW"
        )
        explanation = (
            "The number matches the expected 14-digit shape after conservative OCR normalization. "
            "This is format validation only; no official license-status lookup was performed."
            if format_valid
            else "A license-like number was found, but it does not normalize to 14 digits."
        )
        if corrected_by_ocr:
            explanation += " OCR character correction was applied; confirm the printed number manually."
            verification_status = "NEEDS_MANUAL_REVIEW"
        return {
            "extracted_number": extracted_number,
            "normalized_number": normalized_number,
            "format_valid": format_valid,
            "official_verification_status": verification_status,
            "verification_source": _NO_LICENSE_LOOKUP,
            "confidence": None,
            "explanation": explanation,
            "source_text": source_text,
            "original_ocr_text": label_text,
        }

    parser_field = parsed.get("fssai_license_number")
    parser_value = _raw_value(parser_field)
    source_text = _source_value(parser_field)
    if len(candidates) > 1:
        explanation = "Multiple license-like number candidates were found; select and verify the printed number manually."
        return {
            "extracted_number": None,
            "normalized_number": None,
            "format_valid": None,
            "official_verification_status": "NEEDS_MANUAL_REVIEW",
            "verification_source": _NO_LICENSE_LOOKUP,
            "confidence": None,
            "explanation": explanation,
            "source_text": "\n".join(source for _, source in candidates),
            "original_ocr_text": label_text,
        }
    if parser_value:
        normalized_number = _normalize_license_number(str(parser_value))
        format_valid = bool(re.fullmatch(r"\d{14}", normalized_number))
        return {
            "extracted_number": str(parser_value),
            "normalized_number": normalized_number,
            "format_valid": format_valid,
            "official_verification_status": (
                "NOT_VERIFIED" if format_valid else "NEEDS_MANUAL_REVIEW"
            ),
            "verification_source": _NO_LICENSE_LOOKUP,
            "confidence": None,
            "explanation": (
                "Parsed candidate retained for manual confirmation; no official "
                "license-status lookup was performed."
            ),
            "source_text": source_text,
            "original_ocr_text": label_text,
        }
    return {
        "extracted_number": None,
        "normalized_number": None,
        "format_valid": None,
        "official_verification_status": "NEEDS_MANUAL_REVIEW",
        "verification_source": _NO_LICENSE_LOOKUP,
        "confidence": None,
        "explanation": (
            "No unambiguous license number was extracted. Its absence from OCR "
            "does not establish that the package lacks a license declaration."
        ),
        "source_text": source_text,
        "original_ocr_text": label_text,
    }


def _matching_lines(label_text: str, pattern: re.Pattern[str]) -> list[str]:
    return [line for line in label_text.splitlines() if pattern.search(line)]


def _make_field(
    field_name: str,
    value: Any,
    source_text: str | None,
    *,
    detected: bool | None = None,
    status: str | None = None,
    explanation: str | None = None,
) -> dict[str, Any]:
    exists = value is not None if detected is None else detected
    if status is None:
        status = "PASS" if exists else "MISSING_INFORMATION"
    return {
        "field_name": field_name,
        "detected": exists,
        "extracted_value": value,
        "confidence": None,
        "validation_status": status,
        "explanation": explanation or (
            "A matching label value was detected in OCR text."
            if exists
            else "No matching value was detected in OCR text; applicability is not determined."
        ),
        "source_text": source_text,
    }


def _extract_mandatory_fields(
    label_text: str,
    parsed: dict[str, Any],
    license_information: dict[str, Any],
    date_fields: dict[str, Any],
    reviewed_fields: dict[str, Any] | None = None,
    original_parsed: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    original_parsed = original_parsed or parsed
    product_field = parsed.get("product_name")
    original_product_field = original_parsed.get("product_name")
    ingredients_text = parsed.get("ingredients_text")
    ingredient_items = parsed.get("ingredients")
    nutrient_fields = parsed.get("nutrients", {})
    original_nutrient_fields = original_parsed.get("nutrients", {})
    has_nutrition = any(
        isinstance(field, dict) and field.get("value") is not None
        for field in nutrient_fields.values()
    ) or bool(re.search(r"\bnutrition(?:al)?\s+(?:information|facts|value)\b", label_text, re.I))
    declared = _raw_value(parsed.get("allergens"))
    may_contain = _raw_value(parsed.get("may_contain"))
    veg_info = _vegetarian_information(label_text, ingredient_items)
    fields = [
        _make_field(
            "name_of_food",
            _raw_value(product_field),
            _source_value(original_product_field) or _source_value(product_field),
        ),
        _make_field(
            "ingredient_list",
            ingredients_text,
            _source_value(original_parsed.get("extracted_fields", {}).get("ingredients_text"))
            or _source_value(parsed.get("extracted_fields", {}).get("ingredients_text")),
            status=(
                "PASS"
                if ingredient_items is not None
                else "NEEDS_MANUAL_REVIEW"
                if ingredients_text
                else "MISSING_INFORMATION"
            ),
            explanation=(
                "Ingredient text was extracted and split into readable items."
                if ingredient_items is not None
                else "Ingredient text was found but could not be reliably split; review the OCR."
                if ingredients_text
                else "No ingredient declaration was detected in OCR text."
            ),
        ),
        _make_field(
            "nutrition_information",
            "Nutrition values detected" if has_nutrition else None,
            "\n".join(
                field["source_text"]
                for field in original_nutrient_fields.values()
                if isinstance(field, dict) and field.get("source_text")
            ) or None,
            detected=has_nutrition,
        ),
        _make_field(
            "allergen_declaration",
            {"contains": declared, "may_contain": may_contain}
            if declared or may_contain
            else None,
            "\n".join(
                source
                for source in (
                    _source_value(original_parsed.get("allergens")),
                    _source_value(original_parsed.get("may_contain")),
                )
                if source
            ) or None,
            detected=bool(declared or may_contain),
            explanation=(
                "An explicit allergen or precautionary declaration was extracted."
                if declared or may_contain
                else "No explicit allergen declaration was detected; ingredient/category applicability and OCR completeness require review."
            ),
        ),
        _make_field(
            "vegetarian_declaration",
            veg_info["declaration"],
            veg_info["source_text"],
            detected=veg_info["declaration"] is not None,
            status=veg_info["status"],
            explanation=veg_info["explanation"],
        ),
        _make_field(
            "fssai_license_number",
            license_information["normalized_number"],
            license_information.get("original_source_text")
            or license_information["source_text"],
            detected=license_information["normalized_number"] is not None,
            status="NEEDS_MANUAL_REVIEW",
            explanation=(
                "A number-like value was detected; its format result is separate "
                "from official license verification. "
                + license_information["explanation"]
            ),
        ),
    ]
    for field_name, pattern in _FIELD_PATTERNS.items():
        lines = _matching_lines(label_text, pattern)
        fields.append(
            _make_field(
                field_name,
                "\n".join(lines) if lines else None,
                "\n".join(lines) if lines else None,
                detected=bool(lines),
            )
        )
    date_by_type = {
        "manufacturing_date": "manufacturing_date",
        "packing_date": "packing_date",
        "best_before": "best_before_date",
        "expiry_date": "expiry_use_by_date",
    }
    for date_type, field_name in date_by_type.items():
        items = [
            item
            for item in date_fields.get("original_ocr_dates", date_fields["dates"])
            if item["date_type"] == date_type
        ]
        fields.append(
            _make_field(
                field_name,
                [item["raw_value"] for item in items] or None,
                "\n".join(item["source_text"] for item in items if item.get("source_text")) or None,
                detected=bool(items),
                status=(
                    "NEEDS_MANUAL_REVIEW"
                    if any(item["classification"] == "NEEDS_MANUAL_REVIEW" for item in items)
                    else "POTENTIAL_ISSUE"
                    if any(item["classification"] == "POTENTIAL_ISSUE" for item in items)
                    else "PASS"
                    if items
                    else "MISSING_INFORMATION"
                ),
                explanation=(
                    "Explicitly labeled date text was detected; its normalized interpretation is reported separately."
                    if items
                    else "No date with this label was detected. Other date types are not assumed to be equivalent."
                ),
            )
        )
    fields.append(
        _make_field(
            "date_markings",
            date_fields["dates"] or None,
            "\n".join(
                item["source_text"]
                for item in date_fields.get("original_ocr_dates", date_fields["dates"])
                if item.get("source_text")
            ) or None,
            detected=bool(date_fields["dates"]),
            status=date_fields["status"] if date_fields["dates"] else "MISSING_INFORMATION",
            explanation=date_fields["explanation"],
        )
    )
    reviewed_fields = reviewed_fields or {}
    for field in fields:
        corrected_value = reviewed_fields.get(field["field_name"])
        if not isinstance(corrected_value, (str, int, float, list, dict)):
            continue
        if isinstance(corrected_value, str):
            corrected_value = corrected_value.strip()
        field["original_extracted_value"] = field["extracted_value"]
        field["extracted_value"] = corrected_value
        field["correction_applied"] = True
        field["detected"] = corrected_value not in ("", [], {})
        if field["detected"]:
            field["validation_status"] = "PASS"
            field["explanation"] = (
                "User-confirmed correction used as the final value; original OCR evidence remains available separately."
            )
        else:
            field["validation_status"] = "NEEDS_MANUAL_REVIEW"
            field["explanation"] = "The corrected field is blank; no regulatory conclusion is inferred."
    license_field = next(
        (field for field in fields if field["field_name"] == "fssai_license_number"),
        None,
    )
    if license_field and license_information.get("correction_applied"):
        license_field["original_extracted_value"] = license_information.get(
            "original_ocr_number"
        )
    return fields


def _parse_date(raw_value: str) -> tuple[str | None, str | None, str | None]:
    normalized_ocr = re.sub(
        r"(?<=\d)[OoQ](?=\d)|(?<=\d)[Il](?=[\d./-])",
        lambda match: _OCR_DIGIT_MAP[match.group(0).upper()],
        raw_value.strip(),
    )
    token_match = _DATE_TOKEN.search(normalized_ocr)
    if token_match is None:
        return None, "NEEDS_MANUAL_REVIEW", "No complete calendar date could be parsed; no shelf life was inferred."
    token = token_match.group(0).strip().replace(",", "")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(token, fmt).date().isoformat(), "PASS", None
        except ValueError:
            pass
    numeric = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", token)
    if numeric:
        first, second = int(numeric.group(1)), int(numeric.group(2))
        year_text = numeric.group(3)
        if len(year_text) == 2:
            return None, "NEEDS_MANUAL_REVIEW", "The year has two digits and its century is not inferred."
        day, month = first, second
        if first <= 12 and second <= 12:
            return None, "NEEDS_MANUAL_REVIEW", "The numeric date is ambiguous because both day/month orders are possible."
        if first > 12 and second <= 12:
            day, month = first, second
        elif second > 12 and first <= 12:
            month, day = first, second
        else:
            return None, "NEEDS_MANUAL_REVIEW", "The numeric date does not identify a valid day/month order."
        try:
            return date(int(year_text), month, day).isoformat(), "PASS", None
        except ValueError:
            return None, "NEEDS_MANUAL_REVIEW", "The printed date is impossible."
    month_year = re.fullmatch(r"(\d{1,2})[./-](\d{4})", token)
    if month_year:
        month, year = (int(value) for value in month_year.groups())
        if not 1 <= month <= 12:
            return None, "NEEDS_MANUAL_REVIEW", "The month value is impossible."
        return f"{year:04d}-{month:02d}", "PASS", "Only month and year were printed."
    month_year_name = re.fullmatch(r"([A-Za-z]{3,9})\s+(\d{4})", token)
    if month_year_name:
        month = _MONTH_NAMES.get(month_year_name.group(1).casefold())
        if month is None:
            return None, "NEEDS_MANUAL_REVIEW", "The printed month name is not recognized."
        return f"{int(month_year_name.group(2)):04d}-{month:02d}", "PASS", "Only month and year were printed."
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"):
        try:
            parsed_date = datetime.strptime(token, fmt).date()
            return parsed_date.isoformat(), "PASS", None
        except ValueError:
            continue
    return None, "NEEDS_MANUAL_REVIEW", "The printed date could not be normalized."


def _date_information(label_text: str, *, as_of_date: date | None = None) -> dict[str, Any]:
    as_of_date = as_of_date or date.today()
    results = []
    for line in label_text.splitlines():
        for kind, pattern in _DATE_LABELS.items():
            match = pattern.search(line)
            if match is None:
                continue
            remainder = line[match.end() :].strip(" \t:;#-")
            raw_value_match = _DATE_TOKEN.search(remainder)
            raw_value = raw_value_match.group(0) if raw_value_match else remainder or None
            normalized_date, classification, note = (
                _parse_date(raw_value) if raw_value else (None, "NEEDS_MANUAL_REVIEW", "Date value is missing.")
            )
            result_classification = classification
            if normalized_date and len(normalized_date) == 10:
                parsed_date = date.fromisoformat(normalized_date)
                if kind in {"expiry_date"} and parsed_date < as_of_date:
                    result_classification = "POTENTIAL_ISSUE"
                    note = "The printed expiry date is before the analysis date; verify the package and date interpretation."
                elif kind == "best_before" and parsed_date < as_of_date:
                    result_classification = "NEEDS_MANUAL_REVIEW"
                    note = "The best-before date has passed; this is not an expiry or product-safety determination."
            results.append(
                {
                    "date_type": kind,
                    "raw_value": raw_value,
                    "normalized_date": normalized_date,
                    "classification": result_classification,
                    "explanation": note or "Date was normalized from the labeled OCR text.",
                    "source_text": line,
                    "confidence": None,
                }
            )
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_kind.setdefault(result["date_type"], []).append(result)
    for items in by_kind.values():
        normalized_values = {item["normalized_date"] for item in items if item["normalized_date"]}
        if len(items) > 1 and (len(normalized_values) > 1 or len(normalized_values) == 0):
            for item in items:
                item["classification"] = "NEEDS_MANUAL_REVIEW"
                item["explanation"] = "Multiple conflicting or ambiguous values were detected for this date type."
    return {
        "dates": results,
        "status": (
            "NOT_EVALUATED"
            if not results
            else "NEEDS_MANUAL_REVIEW"
            if any(item["classification"] == "NEEDS_MANUAL_REVIEW" for item in results)
            else "POTENTIAL_ISSUE"
            if any(item["classification"] == "POTENTIAL_ISSUE" for item in results)
            else "PASS"
        ),
        "shelf_life_inferred": False,
        "explanation": (
            "Only explicitly labeled dates were inspected. Relative shelf-life text is not converted into a date."
        ),
    }


def _apply_reviewed_dates(
    date_report: dict[str, Any],
    reviewed_fields: dict[str, Any],
    *,
    as_of_date: date | None = None,
) -> None:
    date_report["original_ocr_dates"] = deepcopy(date_report["dates"])
    date_field_types = {
        "manufacturing_date": "manufacturing_date",
        "packing_date": "packing_date",
        "best_before_date": "best_before",
        "expiry_use_by_date": "expiry_date",
    }
    as_of_date = as_of_date or date.today()
    for field_name, date_type in date_field_types.items():
        value = reviewed_fields.get(field_name)
        if not isinstance(value, str) or not value.strip():
            continue
        raw_value = value.strip()
        normalized_date, classification, note = _parse_date(raw_value)
        if normalized_date and len(normalized_date) == 10:
            parsed_date = date.fromisoformat(normalized_date)
            if date_type == "expiry_date" and parsed_date < as_of_date:
                classification = "POTENTIAL_ISSUE"
                note = "The user-confirmed expiry date is before the analysis date; verify the package and date interpretation."
            elif date_type == "best_before" and parsed_date < as_of_date:
                classification = "NEEDS_MANUAL_REVIEW"
                note = "The user-confirmed best-before date has passed; this is not an expiry or product-safety determination."
        original_values = [
            item["raw_value"]
            for item in date_report["dates"]
            if item["date_type"] == date_type
        ]
        date_report["dates"] = [
            item for item in date_report["dates"] if item["date_type"] != date_type
        ]
        date_report["dates"].append(
            {
                "date_type": date_type,
                "raw_value": raw_value,
                "normalized_date": normalized_date,
                "classification": classification,
                "explanation": note or "Date was confirmed by the user; no shelf life was inferred.",
                "source_text": None,
                "confidence": None,
                "correction_applied": True,
                "original_ocr_values": original_values,
            }
        )
    date_report["dates"].sort(
        key=lambda item: (
            item["date_type"],
            item["source_text"] is None,
        )
    )
    date_report["status"] = (
        "NOT_EVALUATED"
        if not date_report["dates"]
        else "POTENTIAL_ISSUE"
        if any(item["classification"] == "POTENTIAL_ISSUE" for item in date_report["dates"])
        else "NEEDS_MANUAL_REVIEW"
        if any(item["classification"] == "NEEDS_MANUAL_REVIEW" for item in date_report["dates"])
        else "PASS"
    )


def _vegetarian_information(
    label_text: str,
    ingredients: list[str] | None,
    knowledge_records: list[dict] | None = None,
    symbol_detection: dict[str, Any] | None = None,
    symbol_review: str | None = None,
) -> dict[str, Any]:
    veg_matches = [line for line in label_text.splitlines() if _VEG_PATTERNS["vegetarian"].search(line)]
    nonveg_matches = [
        line for line in label_text.splitlines()
        if _VEG_PATTERNS["non_vegetarian"].search(line)
    ]
    declaration = (
        "BOTH_CONFLICTING"
        if veg_matches and nonveg_matches
        else "NON_VEGETARIAN"
        if nonveg_matches
        else "VEGETARIAN"
        if veg_matches
        else None
    )
    text = " ".join(ingredients or [])
    matches = []
    if text:
        ingredient_report = analyze_ingredients(
            ingredients,
            ingredients_available=True,
            knowledge_records=knowledge_records,
        )
        for item in ingredient_report.get("ingredients", []):
            status = item.get("vegetarian_status")
            if status in {"vegetarian", "non_vegetarian", "non-vegetarian"}:
                matches.append(
                    {
                        "ingredient": item.get("original_label_text"),
                        "vegetarian_status": status,
                    }
                )
    known_nonveg = any(item["vegetarian_status"] in {"non_vegetarian", "non-vegetarian"} for item in matches)
    conflict = declaration == "VEGETARIAN" and known_nonveg
    if declaration == "BOTH_CONFLICTING" or conflict:
        status = "POTENTIAL_ISSUE"
        explanation = "Textual declaration and available ingredient data appear inconsistent; inspect the original package manually."
    elif declaration is None:
        status = "MISSING_INFORMATION"
        explanation = "No textual vegetarian/non-vegetarian declaration was detected. Image-based symbol detection is reported separately."
    else:
        status = "NEEDS_MANUAL_REVIEW"
        explanation = "A textual declaration was detected, but OCR text alone does not verify the required printed symbol."
    symbol_detection = symbol_detection or {}
    visual_review_status = (
        "USER_REJECTED"
        if symbol_review == "REJECTED"
        else "USER_CONFIRMED"
        if symbol_review in {"VEGETARIAN", "NON_VEGETARIAN"}
        else "NEEDS_MANUAL_REVIEW"
        if symbol_review == "NEEDS_MANUAL_REVIEW"
        else "NEEDS_MANUAL_REVIEW"
        if any(
            symbol_detection.get(kind, {}).get("status") in {"DETECTED", "NEEDS_MANUAL_REVIEW"}
            for kind in ("vegetarian", "non_vegetarian")
        )
        else "NOT_DETECTED"
        if symbol_detection.get("image_inspected")
        else "NOT_EVALUATED"
    )
    return {
        "declaration": declaration,
        "source_text": "\n".join(veg_matches + nonveg_matches) or None,
        "textual_declaration_detected": declaration is not None,
        "symbol_image_inspected": bool(symbol_detection.get("image_inspected")),
        "symbol_verification_status": visual_review_status,
        "image_symbol_detection": symbol_detection or {
            "image_inspected": False,
            "vegetarian": {"status": "NOT_EVALUATED"},
            "non_vegetarian": {"status": "NOT_EVALUATED"},
        },
        "user_symbol_review": symbol_review,
        "ingredient_matches": matches,
        "potential_conflict": conflict or declaration == "BOTH_CONFLICTING",
        "status": status,
        "explanation": explanation,
    }


def _nutrition_information(
    label_text: str,
    parsed: dict[str, Any],
    original_parsed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    nutrients = parsed.get("nutrients", {})
    original_nutrients = (original_parsed or parsed).get("nutrients", {})
    entries = []
    all_sources = []
    for name, field in nutrients.items():
        if not isinstance(field, dict):
            continue
        value = field.get("value")
        original_field = original_nutrients.get(name)
        source_text = (
            original_field.get("source_text")
            if isinstance(original_field, dict)
            else field.get("source_text")
        )
        if source_text:
            all_sources.append(source_text)
        if value is None:
            classification = (
                "NEEDS_MANUAL_REVIEW"
                if source_text
                else "NOT_EVALUATED"
            )
            explanation = (
                "A nutrient label was found, but its value or unit could not be resolved."
                if source_text
                else "No value for this nutrient was extracted; its applicability is category-dependent."
            )
        else:
            classification = "PASS"
            explanation = "A single numeric value with a recognized unit was extracted; this is not a regulatory validation."
        entries.append(
            {
                "nutrient": name,
                "value": value,
                "unit": field.get("unit"),
                "basis": parsed.get("basis"),
                "classification": classification,
                "confidence": field.get("confidence"),
                "explanation": explanation,
                "source_text": source_text,
            }
        )

    parsed_values = {
        item["nutrient"]: item["value"]
        for item in entries
        if item["value"] is not None
    }
    inconsistencies = []
    total_sugar = parsed_values.get("sugar_g")
    added_sugar = parsed_values.get("added_sugar_g")
    if total_sugar is not None and added_sugar is not None and added_sugar > total_sugar:
        inconsistencies.append(
            {
                "classification": "POTENTIAL_ISSUE",
                "finding": "Added sugars exceed total sugars in the extracted values.",
                "source_text": "\n".join(
                    item["source_text"]
                    for item in entries
                    if item["nutrient"] in {"sugar_g", "added_sugar_g"} and item["source_text"]
                ),
                "explanation": "Possible OCR, unit, serving-basis, or transcription inconsistency; not a legal violation determination.",
            }
        )
    total_fat = parsed_values.get("total_fat_g")
    saturated_fat = parsed_values.get("saturated_fat_g")
    if total_fat is not None and saturated_fat is not None and saturated_fat > total_fat:
        inconsistencies.append(
            {
                "classification": "POTENTIAL_ISSUE",
                "finding": "Saturated fat exceeds total fat in the extracted values.",
                "source_text": "\n".join(
                    item["source_text"]
                    for item in entries
                    if item["nutrient"] in {"total_fat_g", "saturated_fat_g"} and item["source_text"]
                ),
                "explanation": "Possible OCR, unit, serving-basis, or transcription inconsistency; verify the original panel.",
            }
        )
    panel_detected = bool(re.search(r"\bnutrition(?:al)?\s+(?:information|facts|value)\b", label_text, re.I)) or any(
        item["value"] is not None or item["source_text"] for item in entries
    )
    return {
        "status": (
            "NOT_EVALUATED"
            if not panel_detected
            else "POTENTIAL_ISSUE"
            if inconsistencies
            else "NEEDS_MANUAL_REVIEW"
            if any(item["classification"] == "NEEDS_MANUAL_REVIEW" for item in entries)
            else "PASS"
        ),
        "panel_detected": panel_detected,
        "basis": parsed.get("basis"),
        "basis_source_text": _source_value(
            (original_parsed or parsed).get("extracted_fields", {}).get("basis")
        ),
        "nutrients": entries,
        "inconsistencies": inconsistencies,
        "explanation": (
            "Only directly extracted values and conservative consistency checks are reported. "
            "Missing nutrient values are not interpreted as zero or as a violation."
        ),
    }


def _ingredient_information(
    parsed: dict[str, Any],
    knowledge_records: list[dict] | None,
    original_parsed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ingredient_text = parsed.get("ingredients_text")
    items = parsed.get("ingredients")
    if items is None and ingredient_text:
        items = split_ingredients_text(ingredient_text)
    analysis = analyze_ingredients(
        items,
        ingredients_available=ingredient_text is not None,
        knowledge_records=knowledge_records,
    )
    codes = sorted(
        set(
            re.findall(
                r"\b(?:INS|E)\s*[- ]?\s*\d{3,4}[A-Za-z]?(?:\([ivx]+\))?\b",
                ingredient_text or "",
                re.IGNORECASE,
            )
        )
    )
    compound = [
        item for item in (items or [])
        if re.search(r"\([^()]*[,;][^()]*\)", item)
    ]
    return {
        "status": (
            "NOT_EVALUATED"
            if ingredient_text is None
            else "NEEDS_MANUAL_REVIEW"
            if items is None
            else "PASS"
        ),
        "detected": ingredient_text is not None,
        "readable": items is not None,
        "original_text": (
            original_parsed.get("ingredients_text")
            if original_parsed is not None
            else ingredient_text
        ),
        "final_text": ingredient_text,
        "source_text": (
            _source_value(
                (original_parsed or parsed).get("extracted_fields", {}).get("ingredients_text")
            )
        ),
        "normalized_ingredients": items,
        "compound_ingredients": compound,
        "additive_identifiers": codes,
        "analysis": analysis,
        "explanation": (
            "Ingredient names and additive identifiers are text matches only; OCR omissions do not establish ingredient absence."
        ),
    }


def _allergen_information(
    parsed: dict[str, Any],
    ingredient_report: dict[str, Any],
    knowledge_records: list[dict] | None,
    original_parsed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    declared = _raw_value(parsed.get("allergens")) or []
    may_contain = _raw_value(parsed.get("may_contain")) or []
    ingredients_text = ingredient_report.get("final_text") or ""
    ingredient_matches = []
    for canonical_name in ALLERGEN_ALIASES:
        alias = (
            match_allergen_text(
                canonical_name,
                ingredients_text,
                knowledge_records=knowledge_records,
            )
            if ingredients_text
            else None
        )
        if alias:
            ingredient_matches.append(
                {
                    "allergen": canonical_name,
                    "matched_text": alias,
                    "evidence_type": (
                        "POSSIBLE_USER_CORRECTED_TEXT_MATCH"
                        if ingredient_report.get("original_text")
                        != ingredient_report.get("final_text")
                        else "POSSIBLE_OCR_DERIVED_MATCH"
                    ),
                    "source_text": ingredients_text,
                    "confidence": None,
                }
            )
    declared_source = _source_value(
        (original_parsed or parsed).get("allergens")
    )
    may_source = _source_value(
        (original_parsed or parsed).get("may_contain")
    )
    declared_corrected = (
        _source_value(parsed.get("allergens"))
        == "User-confirmed correction; original OCR is retained separately."
    )
    may_contain_corrected = (
        _source_value(parsed.get("may_contain"))
        == "User-confirmed correction; original OCR is retained separately."
    )
    original_declared = (
        _raw_value(original_parsed.get("allergens")) or []
        if original_parsed is not None
        else declared
    )
    original_may_contain = (
        _raw_value(original_parsed.get("may_contain")) or []
        if original_parsed is not None
        else may_contain
    )
    missing_declared = [
        item["allergen"]
        for item in ingredient_matches
        if not any(
            match_allergen_text(
                item["allergen"],
                value,
                knowledge_records=knowledge_records,
            )
            for value in declared
        )
    ]
    return {
        "status": (
            "NEEDS_MANUAL_REVIEW"
            if missing_declared or ingredient_matches
            else "PASS"
            if declared or may_contain
            else "NOT_EVALUATED"
        ),
        "explicit_allergen_declarations": [
            {
                "value": value,
                "evidence_type": (
                    "USER_CONFIRMED_CORRECTION"
                    if declared_corrected
                    else "EXPLICIT_DECLARATION"
                ),
                "source_text": declared_source,
            }
            for value in declared
        ],
        "original_ocr_explicit_allergen_declarations": original_declared,
        "may_contain_declarations": [
            {
                "value": value,
                "evidence_type": (
                    "USER_CONFIRMED_CORRECTION"
                    if may_contain_corrected
                    else "MAY_CONTAIN_STATEMENT"
                ),
                "source_text": may_source,
            }
            for value in may_contain
        ],
        "original_ocr_may_contain_declarations": original_may_contain,
        "ingredient_text_matches": ingredient_matches,
        "confirmed_ingredient_presence": [],
        "potential_conflicts": [
            {
                "allergen": allergen,
                "classification": "NEEDS_MANUAL_REVIEW",
                "explanation": (
                    "An allergen-related ingredient text match has no corresponding explicit declaration in the extracted declaration text. "
                    "Review OCR, ingredient context, and applicable exceptions; this is not a confirmed violation."
                ),
                "ingredient_source_text": ingredients_text,
                "declaration_source_text": declared_source,
            }
            for allergen in missing_declared
        ],
        "safety_conclusion": "NOT_EVALUATED",
        "explanation": (
            "Ingredient text matches, explicit declarations, and precautionary statements are kept distinct. "
            "A missing match never establishes allergen absence or safety."
        ),
    }


def _rule_results(
    field_findings: list[dict[str, Any]],
    product_category: str | None,
) -> list[dict[str, Any]]:
    by_name = {item["field_name"]: item for item in field_findings}
    normalized_category = (product_category or "").casefold().strip()
    results = []
    for rule in LABEL_DETECTION_RULES:
        field = by_name.get(rule.field_name)
        if (
            rule.applicable_categories is not None
            and normalized_category
            and not any(category in normalized_category for category in rule.applicable_categories)
        ):
            applicability = "NOT_APPLICABLE"
            result = "NOT_APPLICABLE"
            explanation = (
                "The configured rule applies only to the listed category keywords; category matching is informational and requires review."
            )
        else:
            applicability = "NEEDS_MANUAL_REVIEW"
            result = field["validation_status"] if field else "NOT_EVALUATED"
            explanation = (
                "This engine evaluates OCR detection only. Applicability, exemptions, and current legal requirements require category-specific review."
            )
        reference = _SOURCES_BY_ID[rule.reference_id]
        results.append(
            {
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "result_classification": result,
                "evaluation_type": "OCR_FIELD_DETECTION_ONLY",
                "applicability_condition": rule.applicability_condition,
                "applicability_status": applicability,
                "product_category": product_category,
                "required_evidence": [rule.field_name],
                "evidence": field.get("source_text") if field else None,
                "explanation": explanation,
                "regulatory_reference": {
                    "source_id": reference["id"],
                    "title": reference["title"],
                    "provisions": reference["provisions"],
                    "source_url": reference["source_url"],
                    "source_version": reference["source_version"],
                    "verification_status": reference["verification_status"],
                    "last_reviewed_date": reference["last_reviewed_date"],
                },
            }
        )
    return results


def analyze_label_compliance(
    label_text: str,
    *,
    product_category: str | None = None,
    as_of_date: date | None = None,
    knowledge_records: list[dict] | None = None,
    label_corrections: dict[str, Any] | None = None,
    corrections_confirmed: bool = False,
    extraction_metadata: dict[str, Any] | None = None,
    symbol_review: str | None = None,
) -> dict[str, Any]:
    """Inspect OCR evidence without making a legal compliance determination."""
    original_parsed = parse_label_text(label_text)
    parsed = deepcopy(original_parsed)
    reviewed_fields = (
        _apply_reviewed_corrections(parsed, label_corrections)
        if corrections_confirmed
        else {}
    )
    original_license_information = _license_information(label_text, original_parsed)
    license_information = _license_information(
        label_text,
        parsed,
        reviewed_number=reviewed_fields.get("fssai_license_number"),
    )
    if license_information.get("correction_applied"):
        license_information["original_ocr_number"] = original_license_information["extracted_number"]
        license_information["original_source_text"] = original_license_information["source_text"]
    date_report = _date_information(label_text, as_of_date=as_of_date)
    if corrections_confirmed:
        _apply_reviewed_dates(date_report, reviewed_fields, as_of_date=as_of_date)
    fields = _extract_mandatory_fields(
        label_text,
        parsed,
        license_information,
        date_report,
        reviewed_fields,
        original_parsed,
    )
    ingredient_report = _ingredient_information(
        parsed,
        knowledge_records,
        original_parsed,
    )
    allergen_report = _allergen_information(
        parsed,
        ingredient_report,
        knowledge_records,
        original_parsed,
    )
    nutrition_report = _nutrition_information(label_text, parsed, original_parsed)
    original_nutrients = original_parsed.get("nutrients", {})
    corrected_nutrients = (
        label_corrections.get("nutrients", {})
        if corrections_confirmed and isinstance(label_corrections, dict)
        else {}
    )
    for nutrient in nutrition_report["nutrients"]:
        original_field = original_nutrients.get(nutrient["nutrient"], {})
        nutrient["original_ocr_value"] = (
            original_field.get("value") if isinstance(original_field, dict) else None
        )
        nutrient["correction_applied"] = nutrient["nutrient"] in corrected_nutrients
    vegetarian_report = _vegetarian_information(
        label_text,
        ingredient_report["normalized_ingredients"],
        knowledge_records,
        symbol_detection=(
            extraction_metadata.get("symbol_detection")
            if isinstance(extraction_metadata, dict)
            and isinstance(extraction_metadata.get("symbol_detection"), dict)
            else None
        ),
        symbol_review=symbol_review if corrections_confirmed else None,
    )

    inconsistencies = [
        *nutrition_report["inconsistencies"],
        *allergen_report["potential_conflicts"],
    ]
    if vegetarian_report["potential_conflict"]:
        inconsistencies.append(
            {
                "classification": "POTENTIAL_ISSUE",
                "finding": "Vegetarian declaration conflicts with another detected declaration or known ingredient record.",
                "source_text": vegetarian_report["source_text"],
                "explanation": vegetarian_report["explanation"],
            }
        )
    if date_report["status"] == "POTENTIAL_ISSUE":
        inconsistencies.extend(
            {
                "classification": item["classification"],
                "finding": f"{item['date_type'].replace('_', ' ').title()} requires review.",
                "source_text": item["source_text"],
                "explanation": item["explanation"],
            }
            for item in date_report["dates"]
            if item["classification"] == "POTENTIAL_ISSUE"
        )

    rules = _rule_results(fields, product_category)
    review_items = [
        {
            "field": item["field_name"],
            "classification": item["validation_status"],
            "reason": item["explanation"],
            "source_text": item["source_text"],
        }
        for item in fields
        if item["validation_status"] in {"MISSING_INFORMATION", "NEEDS_MANUAL_REVIEW"}
    ]
    review_items.extend(
        {
            "field": "nutrition",
            "classification": item["classification"],
            "reason": item["explanation"],
            "source_text": item["source_text"],
        }
        for item in nutrition_report["nutrients"]
        if item["classification"] == "NEEDS_MANUAL_REVIEW"
    )
    confidence_fields = (
        extraction_metadata.get("fields", [])
        if isinstance(extraction_metadata, dict)
        else []
    )
    if isinstance(confidence_fields, list):
        review_items.extend(
            {
                "field": item.get("field_name", "extracted_label_field"),
                "classification": item.get("confidence_state", "NEEDS_MANUAL_REVIEW"),
                "reason": (
                    "OCR confidence is low or unavailable; confirm the value against the original image."
                ),
                "source_text": item.get("source_text"),
            }
            for item in confidence_fields
            if isinstance(item, dict)
            and item.get("confidence_state")
            in {"LOW_CONFIDENCE", "NEEDS_MANUAL_REVIEW"}
        )
    if vegetarian_report["symbol_verification_status"] == "NEEDS_MANUAL_REVIEW":
        review_items.append(
            {
                "field": "vegetarian_symbol",
                "classification": "NEEDS_MANUAL_REVIEW",
                "reason": "An image-based symbol candidate was detected but has not been confirmed by the user.",
                "source_text": None,
            }
        )
    review_items.extend(
        {
            "field": "allergens",
            "classification": "NEEDS_MANUAL_REVIEW",
            "reason": item["explanation"],
            "source_text": item["ingredient_source_text"],
        }
        for item in allergen_report["potential_conflicts"]
    )
    review_items.extend(
        {
            "field": item["date_type"],
            "classification": item["classification"],
            "reason": item["explanation"],
            "source_text": item["source_text"],
        }
        for item in date_report["dates"]
        if item["classification"] == "NEEDS_MANUAL_REVIEW"
    )
    review_items.extend(
        {
            "field": "fssai_license_number",
            "classification": "NEEDS_MANUAL_REVIEW",
            "reason": license_information["explanation"],
            "source_text": license_information["source_text"],
        }
        for _ in (
            [1]
            if license_information["official_verification_status"] == "NEEDS_MANUAL_REVIEW"
            else []
        )
    )
    if not label_text.strip():
        overall_status = "NOT_EVALUATED"
    elif any(
        item["classification"] == "POTENTIAL_ISSUE"
        for item in inconsistencies
    ):
        overall_status = "POTENTIAL_ISSUE"
    elif review_items or any(rule["applicability_status"] == "NEEDS_MANUAL_REVIEW" for rule in rules):
        overall_status = "NEEDS_MANUAL_REVIEW"
    else:
        overall_status = "PASS"

    product_name = _raw_value(parsed.get("product_name"))
    product_name_source = (
        _source_value(parsed.get("product_name"))
        or _source_value(original_parsed.get("product_name"))
    )
    image_extraction = None
    if isinstance(extraction_metadata, dict):
        image_extraction = {
            "fields": confidence_fields if isinstance(confidence_fields, list) else [],
            "regions": extraction_metadata.get("regions", []),
            "processing": extraction_metadata.get("processing"),
            "ocr_quality": extraction_metadata.get("ocr_quality"),
            "symbol_detection": extraction_metadata.get("symbol_detection"),
        }
    return {
        "schema_version": "1.0",
        "overall_status": overall_status,
        "legal_compliance_determination": "NOT_EVALUATED",
        "product_information": {
            "product_name": product_name,
            "product_category": product_category,
            "source_text": product_name_source,
            "original_ocr_value": _raw_value(original_parsed.get("product_name")),
        },
        "fssai_license_information": license_information,
        "mandatory_declarations": fields,
        "ingredient_inspection": ingredient_report,
        "allergen_inspection": allergen_report,
        "nutrition_inspection": nutrition_report,
        "date_inspection": date_report,
        "vegetarian_declaration": vegetarian_report,
        "potential_inconsistencies": inconsistencies,
        "manual_review_requirements": review_items,
        "regulatory_rules": rules,
        "regulatory_sources": list(REGULATORY_SOURCES),
        "ocr_limitations": [
            "OCR can omit, merge, or misread label text; image preprocessing and confidence metadata do not establish that a transcription is correct.",
            "Tesseract word-level confidence is not calibrated field truth; unavailable confidence remains unknown.",
            "Color-and-contour symbol matches are heuristic candidates and require visual confirmation.",
            "A field not detected in OCR is not proof that the package lacks that declaration.",
            "Rule outcomes describe text inspection, not legal compliance, certification, or product safety.",
            "Category-specific requirements, exemptions, and amendments not encoded in this rule set require regulatory review.",
        ],
        "source_text": label_text,
        "original_ocr_text": label_text,
        "corrections_applied": bool(corrections_confirmed and label_corrections),
        "user_corrections": {
            "confirmed": bool(corrections_confirmed),
            "values": label_corrections if corrections_confirmed else {},
            "symbol_review": symbol_review if corrections_confirmed else None,
        },
        "image_extraction": image_extraction,
    }

