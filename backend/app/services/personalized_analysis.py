from collections.abc import Sequence

from app.models import User
from app.services.ingredient_analysis import (
    analyze_ingredients,
    contains_exact_phrase,
    match_allergen_text,
)
from app.services.label_analysis import analyze_label
from app.services.label_parser import split_ingredients_text
from app.services.nutrition import EXCESS_CONTRIBUTION_BANDS


_CONDITION_NUTRIENTS = {
    "Diabetes": ("total_sugar", "added_sugar"),
    "Hypertension": ("sodium",),
    "Heart disease": ("sodium", "saturated_fat"),
    "Kidney disease": ("sodium",),
}
_PERSONAL_WARNING_MIN_PERCENT = EXCESS_CONTRIBUTION_BANDS["lower_max_percent"]
_SUGAR_ALIASES = ("sugar", "sugars", "total sugar", "added sugar")
_PKU_ALIASES = ("aspartame", "phenylalanine")
_PERSONAL_ANALYSIS_NOTE = (
    "Personalized findings compare label evidence with the saved profile; "
    "they are informational, do not diagnose or determine medical safety, "
    "and may be incomplete because labels and OCR can be incomplete or wrong."
)


def _as_text_items(items: Sequence[str] | None) -> list[str]:
    return [item.strip() for item in items or [] if item.strip()]


def _expanded_ingredient_items(
    items: Sequence[str] | None,
    knowledge_records: list[dict] | None,
) -> list[str] | None:
    if items is None:
        return None
    result = []
    for item in _as_text_items(items):
        analysis = analyze_ingredients(
            [item],
            ingredients_available=True,
            knowledge_records=knowledge_records,
        )
        for ingredient in analysis["ingredients"]:
            original_text = ingredient.get("original_label_text")
            if original_text and original_text not in result:
                result.append(original_text)
    return result


def _ingredient_match(
    name: str,
    ingredient: str,
    knowledge_records: list[dict] | None,
) -> str | None:
    matched = match_allergen_text(
        name,
        ingredient,
        knowledge_records=knowledge_records,
    )
    if matched:
        return matched
    analysis = analyze_ingredients(
        [ingredient],
        ingredients_available=True,
        knowledge_records=knowledge_records,
    )
    for result in analysis["ingredients"]:
        canonical_name = result.get("normalized_name") or result.get("matched_name")
        if canonical_name:
            matched = match_allergen_text(
                name,
                canonical_name,
                knowledge_records=knowledge_records,
            )
            if matched:
                return matched
    return None


def _collect_allergen_findings(
    *,
    allergen_names: Sequence[str],
    ingredient_items: Sequence[str] | None,
    declared_allergens: Sequence[str] | None,
    may_contain: Sequence[str] | None,
    knowledge_records: list[dict] | None,
) -> list[dict]:
    findings = []
    seen = set()

    def add_finding(allergen: str, source: str, matched_text: str) -> None:
        key = (allergen.casefold(), source, matched_text.casefold())
        if key in seen:
            return
        seen.add(key)
        precautionary = source == "may_contain_statement"
        findings.append(
            {
                "allergen": allergen,
                "detection_source": source,
                "category": (
                    "precautionary_warning"
                    if precautionary
                    else "ingredient_match"
                    if source == "ingredient"
                    else "declared_allergen_match"
                ),
                "severity": "warning" if precautionary else "detected_concern",
                "matched_text": matched_text,
                "explanation": (
                    "The label says this allergen may be present; this is a "
                    "precautionary statement, not confirmation that it is an "
                    "ingredient."
                    if precautionary
                    else (
                        f"The label's {source.replace('_', ' ')} text matches "
                        f"the saved {allergen} preference. This match is not a "
                        "measurement of exposure or an assessment of an "
                        "individual reaction."
                    )
                ),
            }
        )

    for allergen in allergen_names:
        for item in _as_text_items(ingredient_items):
            matched_alias = _ingredient_match(
                allergen,
                item,
                knowledge_records,
            )
            if matched_alias:
                add_finding(allergen, "ingredient", item)
        for declaration in _as_text_items(declared_allergens):
            if match_allergen_text(
                allergen,
                declaration,
                knowledge_records=knowledge_records,
            ):
                add_finding(allergen, "declared_allergen", declaration)
        for declaration in _as_text_items(may_contain):
            if match_allergen_text(
                allergen,
                declaration,
                knowledge_records=knowledge_records,
            ):
                add_finding(allergen, "may_contain_statement", declaration)
    return findings


def _profile_factors(user: User) -> tuple[list[str], list[str]]:
    conditions = [
        selection.condition.name
        for selection in user.health_condition_selections
        if selection.condition is not None
    ]
    allergens = []
    for selection in user.allergen_selections:
        if selection.allergen is not None:
            allergens.append(selection.allergen.name)
        elif selection.custom_allergen_name:
            allergens.append(selection.custom_allergen_name)
    return conditions, allergens


def _condition_nutrition_findings(
    condition: str,
    excess_nutrients: Sequence[dict],
) -> tuple[list[dict], list[str]]:
    nutrient_names = _CONDITION_NUTRIENTS[condition]
    assessments = {
        assessment["nutrient"]: assessment
        for assessment in excess_nutrients
    }
    findings = []
    missing = []

    for nutrient_name in nutrient_names:
        assessment = assessments.get(nutrient_name)
        if assessment is None or assessment["status"] == "Unable to assess":
            missing.append(
                f"{nutrient_name.replace('_', ' ').capitalize()} could not be "
                "assessed from the available value, unit, serving basis, or "
                "serving-size information."
            )
            continue

        percentage = assessment["percentage_of_project_reference"]
        if percentage is not None and percentage >= _PERSONAL_WARNING_MIN_PERCENT:
            findings.append(
                {
                    "finding_type": "nutrient_reference_signal",
                    "severity": "warning",
                    "title": f"{assessment['nutrient'].replace('_', ' ').capitalize()} label value",
                    "description": (
                        f"{assessment['value']:g} {assessment['unit']} on the "
                        f"reported basis is {percentage:g}% of the configured "
                        "project reference. This is a label comparison, not "
                        "a condition-specific medical threshold."
                    ),
                    "evidence": {
                        "value": assessment["value"],
                        "unit": assessment["unit"],
                        "basis": assessment["basis"],
                        "project_reference_value": assessment[
                            "project_reference_value"
                        ],
                        "percentage_of_project_reference": percentage,
                    },
                }
            )
    return findings, missing


def _condition_assessments(
    *,
    conditions: Sequence[str],
    allergen_findings: Sequence[dict],
    ingredient_items: Sequence[str] | None,
    declared_allergens: Sequence[str] | None,
    may_contain: Sequence[str] | None,
    ingredient_text_available: bool,
    allergen_declarations_available: bool,
    excess_nutrients: Sequence[dict],
    knowledge_records: list[dict] | None,
) -> list[dict]:
    assessments = []
    for condition in conditions:
        findings = []
        missing = []
        condition_key = condition.casefold()

        if condition_key == "celiac disease":
            gluten_findings = [
                finding
                for finding in allergen_findings
                if finding["allergen"].casefold() == "gluten"
            ]
            # Celiac disease requires a gluten review even when the user has
            # not separately selected Gluten in the allergen preferences.
            if not any(
                finding["allergen"].casefold() == "gluten"
                for finding in gluten_findings
            ):
                gluten_findings = _collect_allergen_findings(
                    allergen_names=["Gluten"],
                    ingredient_items=ingredient_items,
                    declared_allergens=declared_allergens,
                    may_contain=may_contain,
                    knowledge_records=knowledge_records,
                )
            findings.extend(
                {
                    "finding_type": "gluten_label_evidence",
                    "severity": finding["severity"],
                    "title": f"Gluten-related label text: {finding['matched_text']}",
                    "description": finding["explanation"],
                    "evidence": {
                        "detection_source": finding["detection_source"],
                        "matched_text": finding["matched_text"],
                    },
                }
                for finding in gluten_findings
            )
            if not ingredient_text_available:
                missing.append("The ingredient list is unavailable or unreadable.")
            if not allergen_declarations_available:
                missing.append(
                    "Allergen and may-contain declarations were not available."
                )
            if not findings and (ingredient_text_available or allergen_declarations_available):
                missing.append(
                    "No gluten-related match was found in the available text; "
                    "this does not establish gluten absence or product safety."
                )

        elif condition_key == "pku":
            evidence_sources = [
                ("ingredient", _as_text_items(ingredient_items)),
                ("declared_allergen", _as_text_items(declared_allergens)),
                ("may_contain_statement", _as_text_items(may_contain)),
            ]
            for source, texts in evidence_sources:
                for text in texts:
                    matched = next(
                        (
                            alias
                            for alias in _PKU_ALIASES
                            if contains_exact_phrase(text, alias)
                        ),
                        None,
                    )
                    if matched:
                        findings.append(
                            {
                                "finding_type": "phenylalanine_related_label_evidence",
                                "severity": (
                                    "warning"
                                    if source == "may_contain_statement"
                                    else "detected_concern"
                                ),
                                "title": f"{matched.capitalize()} label text",
                                "description": (
                                    "The label text includes an ingredient or "
                                    "statement associated with phenylalanine. "
                                    "This is label evidence only and is not a "
                                    "medical assessment."
                                ),
                                "evidence": {
                                    "detection_source": source,
                                    "matched_text": text,
                                },
                            }
                        )
            if not ingredient_text_available and not allergen_declarations_available:
                missing.append(
                    "Ingredient and allergen declarations are unavailable."
                )
            if not findings and (
                ingredient_text_available or allergen_declarations_available
            ):
                missing.append(
                    "No aspartame or phenylalanine-related text was found in "
                    "the available label fields; absence is not established."
                )

        elif condition in _CONDITION_NUTRIENTS:
            findings, missing = _condition_nutrition_findings(
                condition,
                excess_nutrients,
            )
            if condition == "Kidney disease":
                missing.append(
                    "The current label pipeline does not assess potassium, "
                    "phosphorus, or other kidney-specific nutrition factors."
                )
            if condition == "Diabetes":
                sugar_assessments = [
                    item
                    for item in excess_nutrients
                    if item["nutrient"] in _SUGAR_ALIASES
                ]
                available_sugar = any(
                    item["status"] != "Unable to assess"
                    for item in sugar_assessments
                )
                if not available_sugar:
                    missing.append(
                        "Neither total sugar nor added sugar could be assessed."
                    )

        elif condition in {"IBS", "Gout"}:
            missing.append(
                "No condition-specific ingredient or nutrient rule is "
                "configured for this condition in this version; no inference "
                "is made."
            )
        else:
            missing.append(
                "This saved condition has no matching analysis rule."
            )

        assessments.append(
            {
                "condition": condition,
                "status": (
                    "findings_present"
                    if findings
                    else "unknown"
                    if missing
                    else "no_project_threshold_signal"
                ),
                "findings": findings,
                "missing_information": list(dict.fromkeys(missing)),
            }
        )
    return assessments


def analyze_personalized_label(
    user: User,
    data,
    *,
    knowledge_records: list[dict] | None = None,
) -> dict:
    general_analysis = analyze_label(data, knowledge_records=knowledge_records)
    conditions, allergens = _profile_factors(user)

    ingredient_items = getattr(data, "ingredients", None)
    ingredients_text = data.ingredients_text
    if ingredient_items is None and ingredients_text is not None:
        ingredient_items = split_ingredients_text(ingredients_text)
    ingredient_items = _expanded_ingredient_items(
        ingredient_items,
        knowledge_records,
    )

    declared_allergens = data.allergens
    may_contain = data.may_contain
    ingredient_text_available = bool(ingredient_items)
    allergen_declarations_available = bool(declared_allergens or may_contain)
    allergen_findings = _collect_allergen_findings(
        allergen_names=allergens,
        ingredient_items=ingredient_items,
        declared_allergens=declared_allergens,
        may_contain=may_contain,
        knowledge_records=knowledge_records,
    )

    allergen_missing = []
    if allergens and not ingredient_text_available:
        allergen_missing.append("The ingredient list is unavailable or unreadable.")
    if allergens and not allergen_declarations_available:
        allergen_missing.append(
            "Allergen and may-contain declarations were not available."
        )
    if not allergens:
        allergen_status = "not_configured"
    elif allergen_findings:
        allergen_status = "matches_found"
    elif allergen_missing:
        allergen_status = "unknown"
    else:
        allergen_status = "no_match_in_available_evidence"

    condition_assessments = _condition_assessments(
        conditions=conditions,
        allergen_findings=allergen_findings,
        ingredient_items=ingredient_items,
        declared_allergens=declared_allergens,
        may_contain=may_contain,
        ingredient_text_available=ingredient_text_available,
        allergen_declarations_available=allergen_declarations_available,
        excess_nutrients=general_analysis["excess_nutrients"],
        knowledge_records=knowledge_records,
    )
    condition_findings = [
        finding
        for assessment in condition_assessments
        for finding in assessment["findings"]
    ]

    detected_concerns = [
        finding
        for finding in allergen_findings
        if finding["severity"] == "detected_concern"
    ]
    warnings = [
        finding
        for finding in allergen_findings
        if finding["severity"] == "warning"
    ] + condition_findings
    missing_information = list(allergen_missing)
    for assessment in condition_assessments:
        missing_information.extend(assessment["missing_information"])
    missing_information = list(dict.fromkeys(missing_information))

    has_profile_factors = bool(conditions or allergens)
    if not has_profile_factors:
        suitability_status = "no_profile_factors"
    elif detected_concerns or warnings:
        suitability_status = "findings_present"
    elif missing_information:
        suitability_status = "unknown"
    else:
        suitability_status = "no_match_in_available_evidence"

    return {
        "general_analysis": general_analysis,
        "personal_suitability": {
            "status": suitability_status,
            "profile_factors": {
                "health_conditions": conditions,
                "allergens": allergens,
            },
            "allergen_assessment": {
                "status": allergen_status,
                "findings": allergen_findings,
                "missing_information": allergen_missing,
            },
            "condition_assessments": condition_assessments,
            "detected_concerns": detected_concerns,
            "warnings": warnings,
            "missing_information": missing_information,
            "note": _PERSONAL_ANALYSIS_NOTE,
        },
    }
