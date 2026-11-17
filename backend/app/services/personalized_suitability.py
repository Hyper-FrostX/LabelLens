import re
from typing import Any

from app.services.ingredient_analysis import contains_exact_phrase

_GOAL_THRESHOLDS = {
    "lower_sugar": {
        "field": "sugar",
        "basis": "per_100",
        "direction": "at_most",
        "value": 5.0,
        "unit": "g",
    },
    "lower_sodium": {
        "field": "sodium",
        "basis": "per_100",
        "direction": "at_most",
        "value": 120.0,
        "unit": "mg",
    },
    "lower_saturated_fat": {
        "field": "saturated_fat",
        "basis": "per_100",
        "direction": "at_most",
        "value": 1.5,
        "unit": "g",
    },
    "lower_calories": {
        "field": "energy",
        "basis": "per_serving",
        "direction": "at_most",
        "value": 200.0,
        "unit": "kcal",
    },
    "higher_protein": {
        "field": "protein",
        "basis": "per_serving",
        "direction": "at_least",
        "value": 5.0,
        "unit": "g",
    },
    "higher_fiber": {
        "field": "fiber",
        "basis": "per_serving",
        "direction": "at_least",
        "value": 3.0,
        "unit": "g",
    },
}


def _assessment(
    factor: str,
    status: str,
    explanation: str,
    evidence: Any = None,
) -> dict:
    result = {
        "factor": factor,
        "status": status,
        "explanation": explanation,
    }
    if evidence is not None:
        result["evidence"] = evidence
    return result


def _label_text(data: Any) -> str:
    sections = [
        data.label_text or "",
        data.ingredients_text or "",
        " ".join(data.ingredients or []),
        " ".join(data.allergens or []),
        " ".join(data.may_contain or []),
    ]
    corrections = data.label_corrections or {}
    if data.corrections_confirmed:
        sections.extend(
            str(value)
            for key, value in corrections.items()
            if key in {"ingredients_text", "allergens", "may_contain"}
            and value is not None
        )
    return " ".join(sections).casefold()


def _profile_values(user: Any) -> dict:
    profile = getattr(user, "health_profile", None)
    if profile is None:
        return {
            "dietary_preferences": [],
            "ingredient_exclusions": [],
            "nutrition_goals": [],
            "calorie_goal_kcal": None,
            "protein_goal_g": None,
        }
    return {
        "dietary_preferences": list(profile.dietary_preferences or []),
        "ingredient_exclusions": list(profile.ingredient_exclusions or []),
        "nutrition_goals": list(profile.nutrition_goals or []),
        "calorie_goal_kcal": profile.calorie_goal_kcal,
        "protein_goal_g": profile.protein_goal_g,
    }


def evaluate_product_suitability(
    *,
    user: Any,
    data: Any,
    intelligence: dict,
    legacy_profile_analysis: dict | None,
) -> dict:
    if user is None:
        return {
            "status": "INSUFFICIENT_INFORMATION",
            "profile_configured": False,
            "assessments": [],
            "profile_alignment_score": None,
            "score_status": "not_evaluated",
            "missing_inputs": ["An authenticated user profile was not available."],
            "explanation": "No profile-based assessment was performed.",
        }

    profile = _profile_values(user)
    conditions = [
        selection.condition.name
        for selection in getattr(user, "health_condition_selections", [])
        if selection.condition is not None
    ]
    allergens = []
    for selection in getattr(user, "allergen_selections", []):
        if selection.allergen is not None:
            allergens.append(selection.allergen.name)
        elif selection.custom_allergen_name:
            allergens.append(selection.custom_allergen_name)
    profile_configured = bool(
        conditions
        or allergens
        or profile["dietary_preferences"]
        or profile["ingredient_exclusions"]
        or profile["nutrition_goals"]
        or profile["calorie_goal_kcal"]
        or profile["protein_goal_g"]
    )
    if not profile_configured:
        return {
            "status": "INSUFFICIENT_INFORMATION",
            "profile_configured": False,
            "assessments": [],
            "profile_alignment_score": None,
            "score_status": "not_evaluated",
            "missing_inputs": ["No supported dietary or nutrition preferences are configured."],
            "explanation": "Save supported profile preferences to enable this assessment.",
        }

    assessments = []
    missing = []
    text = _label_text(data)
    ingredient_values = list(data.ingredients or [])
    if not ingredient_values and data.ingredients_text:
        from app.services.label_parser import split_ingredients_text

        ingredient_values = split_ingredients_text(data.ingredients_text)

    legacy_suitability = (
        (legacy_profile_analysis or {}).get("personal_suitability", {})
    )
    allergen_findings = legacy_suitability.get("detected_concerns", []) + legacy_suitability.get(
        "warnings", []
    )
    matched_allergens = {
        str(item.get("allergen", "")).casefold()
        for item in allergen_findings
        if item.get("allergen")
    }
    for allergen in allergens:
        if allergen.casefold() in matched_allergens:
            assessments.append(
                _assessment(
                    f"allergen:{allergen}",
                    "potential_conflict",
                    "A label-text match was found for this saved allergen. Review the package and consult qualified advice; the match does not quantify exposure.",
                    [item for item in allergen_findings if item.get("allergen", "").casefold() == allergen.casefold()],
                )
            )
        else:
            assessments.append(
                _assessment(
                    f"allergen:{allergen}",
                    "unknown",
                    "No match in submitted text does not establish absence or safety.",
                )
            )
            missing.append(f"allergen evidence for {allergen}")

    condition_assessments = legacy_suitability.get("condition_assessments", [])
    by_condition = {
        item.get("condition", "").casefold(): item
        for item in condition_assessments
    }
    for condition in conditions:
        result = by_condition.get(condition.casefold())
        if result and result.get("findings"):
            assessments.append(
                _assessment(
                    f"condition:{condition}",
                    "potential_conflict",
                    "A supported project rule found a label signal. This is not a condition-specific medical threshold or recommendation.",
                    result,
                )
            )
        else:
            assessments.append(
                _assessment(
                    f"condition:{condition}",
                    "unknown",
                    "No project-rule signal does not establish medical suitability.",
                    result,
                )
            )
            missing.append(f"supported evidence for {condition}")

    symbol_review = data.symbol_review if data.corrections_confirmed else None
    preference_text = text
    for preference in profile["dietary_preferences"]:
        normalized = preference.casefold()
        if normalized == "vegetarian":
            if symbol_review == "NON_VEGETARIAN" or re.search(
                r"\bnon[\s-]?vegetarian\b", preference_text
            ):
                assessments.append(
                    _assessment(
                        f"dietary_preference:{preference}",
                        "potential_conflict",
                        "The reviewed label information indicates a non-vegetarian declaration.",
                        {
                            "symbol_review": symbol_review,
                            "confirmed_declaration": bool(
                                data.corrections_confirmed
                                and (
                                    symbol_review == "NON_VEGETARIAN"
                                    or re.search(
                                        r"\bnon[\s-]?vegetarian\b",
                                        preference_text,
                                    )
                                )
                            ),
                        },
                    )
                )
            elif symbol_review == "VEGETARIAN" or re.search(
                r"\bvegetarian\b", preference_text
            ):
                assessments.append(
                    _assessment(
                        f"dietary_preference:{preference}",
                        "matches",
                        "A vegetarian declaration was identified; this is a label claim, not independent verification.",
                        {"symbol_review": symbol_review},
                    )
                )
            else:
                assessments.append(
                    _assessment(
                        f"dietary_preference:{preference}",
                        "unknown",
                        "No explicit vegetarian declaration was confirmed.",
                    )
                )
                missing.append(f"explicit {preference} declaration")
        elif normalized == "vegan":
            if symbol_review == "NON_VEGETARIAN" or re.search(
                r"\bnon[\s-]?vegan\b",
                preference_text,
            ):
                assessments.append(
                    _assessment(
                        f"dietary_preference:{preference}",
                        "potential_conflict",
                        "The reviewed label information indicates a non-vegan product declaration.",
                        {
                            "symbol_review": symbol_review,
                            "confirmed_declaration": bool(data.corrections_confirmed),
                        },
                    )
                )
            elif re.search(r"\bvegan\b", preference_text):
                assessments.append(
                    _assessment(
                        f"dietary_preference:{preference}",
                        "matches",
                        "An explicit vegan claim was found in submitted text; it is not independently verified.",
                    )
                )
            else:
                assessments.append(
                    _assessment(
                        f"dietary_preference:{preference}",
                        "unknown",
                        "No explicit vegan declaration was confirmed; ingredient names are not used to infer vegan status.",
                    )
                )
                missing.append("explicit vegan declaration")
        else:
            terms = {
                "gluten-free": ("gluten", "gluten free"),
                "dairy-free": ("dairy", "dairy free"),
            }.get(normalized, ())
            escaped_term = (
                re.escape(terms[1]).replace("\\ ", r"[\s-]+")
                if terms
                else ""
            )
            if terms and any(
                contains_exact_phrase(term, ingredient)
                for term in terms[:1]
                for ingredient in ingredient_values
            ):
                assessments.append(
                    _assessment(
                        f"dietary_preference:{preference}",
                        "potential_conflict",
                        "Ingredient text may conflict with the saved dietary preference; the label text may be incomplete.",
                    )
                )
            elif terms and re.search(rf"\b{escaped_term}\b", preference_text):
                assessments.append(
                    _assessment(
                        f"dietary_preference:{preference}",
                        "matches",
                        "An explicit free-from claim was found in submitted text; it is not independently verified.",
                    )
                )
            else:
                assessments.append(
                    _assessment(
                        f"dietary_preference:{preference}",
                        "unknown",
                        "The submitted text does not establish this dietary preference.",
                    )
                )
                missing.append(f"evidence for {preference}")

    for exclusion in profile["ingredient_exclusions"]:
        matching = [
            item
            for item in ingredient_values
            if contains_exact_phrase(exclusion, item)
        ]
        if matching:
            assessments.append(
                _assessment(
                    f"ingredient_exclusion:{exclusion}",
                    "potential_conflict",
                    "The ingredient text matches a saved exclusion. Check the original label because text extraction may be incomplete.",
                    matching,
                )
            )
        else:
            assessments.append(
                _assessment(
                    f"ingredient_exclusion:{exclusion}",
                    "unknown",
                    "No text match does not establish that the excluded ingredient is absent.",
                )
            )
            missing.append(f"ingredient evidence for {exclusion}")

    density = intelligence.get("nutrient_density_per_100", {})
    per_serving = intelligence.get("per_serving", {})
    for goal in profile["nutrition_goals"]:
        rule = _GOAL_THRESHOLDS.get(goal)
        if rule is None:
            assessments.append(
                _assessment(
                    f"nutrition_goal:{goal}",
                    "unknown",
                    "This saved nutrition goal is not supported by the current rule set.",
                )
            )
            missing.append(f"supported rule for {goal}")
            continue
        source = density if rule["basis"] == "per_100" else per_serving
        value = source.get(rule["field"])
        if value is None:
            assessments.append(
                _assessment(
                    f"nutrition_goal:{goal}",
                    "unknown",
                    "The required nutrient value or comparable basis was not available.",
                )
            )
            missing.append(f"nutrient data for {goal}")
            continue
        passes = (
            value["value"] <= rule["value"]
            if rule["direction"] == "at_most"
            else value["value"] >= rule["value"]
        )
        assessments.append(
            _assessment(
                f"nutrition_goal:{goal}",
                "matches" if passes else "potential_conflict",
                (
                    "The reported value meets the Label Lens project goal threshold."
                    if passes
                    else "The reported value does not meet the Label Lens project goal threshold."
                )
                + " Thresholds are informational and not medical targets.",
                {
                    "reported": value,
                    "threshold": rule,
                },
            )
        )

    for nutrient, goal_field in (
        ("energy", "calorie_goal_kcal"),
        ("protein", "protein_goal_g"),
    ):
        if profile[goal_field] is None:
            continue
        value = per_serving.get(nutrient)
        contribution = (
            round(value["value"] * 100 / profile[goal_field], 2)
            if value is not None and profile[goal_field] > 0
            else None
        )
        assessments.append(
            _assessment(
                f"daily_target:{goal_field}",
                "unknown",
                (
                    "A per-serving contribution is shown, but it does not determine "
                    "whether this product fits a daily goal."
                    if value is not None
                    else "A comparable per-serving nutrient value was unavailable."
                ),
                {
                    "label_value_per_serving": value,
                    "user_target_per_day": profile[goal_field],
                    "contribution": contribution,
                },
            )
        )
        if value is None:
            missing.append(f"per-serving {nutrient} for {goal_field}")

    statuses = [item["status"] for item in assessments]
    has_conflict = "potential_conflict" in statuses
    has_unknown = "unknown" in statuses
    explicit_preference_conflict = any(
        item["status"] == "potential_conflict"
        and item["factor"].startswith("dietary_preference:")
        and isinstance(item.get("evidence"), dict)
        and item["evidence"].get("confirmed_declaration")
        for item in assessments
    )
    if explicit_preference_conflict:
        overall = "UNSUITABLE_BASED_ON_USER_PREFERENCES"
    elif has_conflict:
        overall = "POTENTIAL_CONFLICT"
    elif has_unknown:
        overall = "NEEDS_REVIEW"
    else:
        overall = "SUITABLE_BASED_ON_AVAILABLE_DATA"

    evaluated = [
        item for item in assessments
        if item["status"] in {"matches", "potential_conflict"}
    ]
    alignment_score = (
        100
        * sum(item["status"] == "matches" for item in evaluated)
        / len(evaluated)
        if evaluated
        else None
    )
    contributions = {}
    for nutrient, goal_field in (
        ("energy", "calorie_goal_kcal"),
        ("protein", "protein_goal_g"),
    ):
        target = profile.get(goal_field)
        value = per_serving.get(nutrient)
        if target and value and target > 0:
            contributions[goal_field] = {
                "label_amount_per_serving": value,
                "user_target_per_day": target,
                "percent_of_user_target_per_serving": (
                    round(value["value"] * 100 / target, 2)
                    if value["value"] is not None
                    else None
                ),
                "note": "Descriptive contribution only; not a meal or medical recommendation.",
            }

    return {
        "status": overall,
        "profile_configured": True,
        "assessments": assessments,
        "profile_alignment_score": round(alignment_score, 1) if alignment_score is not None else None,
        "score_status": "available" if alignment_score is not None else "insufficient_data",
        "score_meaning": (
            "Percentage of evaluated profile factors without a potential conflict "
            "in submitted data; not a safety or clinical suitability score."
        ),
        "missing_inputs": sorted(set(missing)),
        "goal_contributions": contributions,
        "explanation": (
            "Profile rules compare available submitted label data with saved preferences. "
            "Unknown or missing evidence does not establish safety or absence."
        ),
    }
