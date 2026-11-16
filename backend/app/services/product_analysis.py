from collections.abc import Sequence
import re
from typing import Any

from pydantic import ValidationError

from app.schemas.product_analysis import ProductAnalysisInput
from app.services.additive_detector import detect_additives
from app.services.ingredient_analysis import (
    match_allergen_text,
)
from app.services.label_analysis import analyze_label
from app.services.label_parser import split_ingredients_text
from app.services.personalized_analysis import analyze_personalized_label
from app.services.nutrition_intelligence import build_nutrition_intelligence
from app.services.food_scoring import build_food_scores
from app.services.personalized_suitability import evaluate_product_suitability


_COMPARISON_NUTRIENTS = {
    "energy": ("energy_kcal", "lower"),
    "energy_kcal": ("energy_kcal", "lower"),
    "calories": ("energy_kcal", "lower"),
    "sugar": ("sugar_g", "lower"),
    "total_sugar": ("sugar_g", "lower"),
    "added_sugar": ("added_sugar_g", "lower"),
    "sodium": ("sodium_mg", "lower"),
    "saturated_fat": ("saturated_fat_g", "lower"),
    "trans_fat": ("trans_fat_g", "lower"),
    "fiber": ("fiber_g", "higher"),
    "fibre": ("fiber_g", "higher"),
    "protein": ("protein_g", "higher"),
}

_REC_NUTRIENT_UNITS = {
    "energy_kcal": "kcal",
    "total_fat_g": "g",
    "saturated_fat_g": "g",
    "trans_fat_g": "g",
    "carbohydrates_g": "g",
    "sugar_g": "g",
    "added_sugar_g": "g",
    "protein_g": "g",
    "fiber_g": "g",
    "sodium_mg": "mg",
}


def _candidate_nutrition_values(data: ProductAnalysisInput) -> tuple[str | None, dict]:
    intelligence = build_nutrition_intelligence(data)
    if intelligence.get("normalized_basis") not in {"per_100g", "per_100ml"}:
        return None, {}
    source_to_field = {
        "energy": "energy_kcal",
        "total_fat": "total_fat_g",
        "saturated_fat": "saturated_fat_g",
        "trans_fat": "trans_fat_g",
        "carbohydrates": "carbohydrates_g",
        "sugar": "sugar_g",
        "added_sugar": "added_sugar_g",
        "protein": "protein_g",
        "fiber": "fiber_g",
        "sodium": "sodium_mg",
    }
    return intelligence["normalized_basis"], {
        source_to_field[name]: item["value"]
        for name, item in intelligence["nutrient_density_per_100"].items()
        if name in source_to_field
        and item.get("basis") == intelligence["normalized_basis"]
    }


def _catalog_product_analysis_input(product, comparison_basis: str) -> ProductAnalysisInput:
    core_fields = {
        "sugar_g": "sugar_g",
        "added_sugar_g": "added_sugar_g",
        "sodium_mg": "sodium_mg",
        "saturated_fat_g": "saturated_fat_g",
    }
    unit_fields = {
        "sugar_g": "sugar_unit",
        "added_sugar_g": "added_sugar_unit",
        "sodium_mg": "sodium_unit",
        "saturated_fat_g": "saturated_fat_unit",
    }
    core = {}
    additional = {}
    product_basis = comparison_basis
    nutrients = [
        nutrient
        for nutrient in product.nutrients
        if nutrient.basis.value == comparison_basis
    ]
    if not nutrients and getattr(product, "serving_size_text", None):
        nutrients = [
            nutrient
            for nutrient in product.nutrients
            if nutrient.basis.value == "per_serving"
        ]
        if nutrients:
            product_basis = "per_serving"
    for nutrient in nutrients:
        mapped = _COMPARISON_NUTRIENTS.get(
            re.sub(r"[^a-z0-9]+", "_", nutrient.nutrient_name.casefold()).strip("_")
        )
        if mapped is None:
            continue
        field_name, _direction = mapped
        unit = nutrient.unit.casefold().strip()
        if field_name in core_fields:
            core_field = core_fields[field_name]
            core[core_field] = float(nutrient.amount)
            core[unit_fields[core_field]] = unit
            continue
        nutrient_name = (
            "energy_kj"
            if field_name == "energy_kcal" and unit == "kj"
            else field_name
        )
        if nutrient_name not in {
            "energy_kcal",
            "energy_kj",
            "total_fat_g",
            "trans_fat_g",
            "carbohydrates_g",
            "protein_g",
            "fiber_g",
        }:
            continue
        additional[nutrient_name] = {
            "value": float(nutrient.amount),
            "unit": unit,
        }
    return ProductAnalysisInput(
        product_name=product.product_name,
        product_category=product.category,
        basis=product_basis,
        serving_size_text=getattr(product, "serving_size_text", None),
        ingredients=[
            item.original_label_text
            for item in getattr(product, "ingredients", [])
        ] or None,
        ingredients_text=getattr(product, "ingredients_text", None),
        allergens=getattr(product, "declared_allergens", None),
        may_contain=getattr(product, "may_contain", None),
        additional_nutrients=additional,
        **core,
    )


def _report_alternatives(
    data: ProductAnalysisInput,
    products: Sequence,
    *,
    current_user=None,
) -> dict:
    comparison_basis, comparable_current = _candidate_nutrition_values(data)
    if comparison_basis is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "items": [],
            "recommendation_goal": data.recommendation_goal,
            "reason": "A compatible per-100 g or per-100 ml basis could not be established from the label and serving size.",
        }
    if len(comparable_current) < 2:
        return {
            "status": "INSUFFICIENT_DATA",
            "items": [],
            "recommendation_goal": data.recommendation_goal,
            "reason": "At least two comparable nutrient values and a per-100 basis are required.",
        }

    recommendations = []
    user_profile = getattr(current_user, "health_profile", None)
    preferred_goals = (
        user_profile.nutrition_goals or []
        if user_profile is not None
        else []
    )
    effective_goal = data.recommendation_goal
    if effective_goal == "balanced":
        effective_goal = next(
            (
                goal
                for goal in preferred_goals
                if goal in {
                    "lower_sugar",
                    "lower_sodium",
                    "lower_saturated_fat",
                    "higher_protein",
                    "higher_fiber",
                    "lower_calories",
                }
            ),
            "balanced",
        )
    goal_nutrient = {
        "lower_sugar": "sugar_g",
        "lower_sodium": "sodium_mg",
        "lower_saturated_fat": "saturated_fat_g",
        "higher_protein": "protein_g",
        "higher_fiber": "fiber_g",
        "lower_calories": "energy_kcal",
    }.get(effective_goal)
    for product in products:
        candidate_input = None
        if isinstance(product, dict):
            candidate_input = product.get("input", product)
            if not isinstance(candidate_input, dict):
                continue
            product_name = (
                product.get("product_name")
                or candidate_input.get("product_name")
                or product.get("name")
            )
            if not product_name:
                product_name = "Saved product"
            if (
                (
                    data.product_category
                    and candidate_input.get("product_category")
                    and candidate_input["product_category"].casefold()
                    != data.product_category.casefold()
                )
                or (
                    data.product_name
                    and product_name.casefold() == data.product_name.casefold()
                )
            ):
                continue
            try:
                candidate_data = ProductAnalysisInput.model_validate(candidate_input)
            except ValidationError:
                continue
            candidate_basis, candidate_values = _candidate_nutrition_values(
                candidate_data
            )
            if candidate_basis != comparison_basis:
                continue
        else:
            product_name = product.product_name
            if (
                data.product_category
                and product.category
                and product.category.casefold() != data.product_category.casefold()
            ):
                continue
            candidate_data = _catalog_product_analysis_input(
                product,
                comparison_basis,
            )
            candidate_basis, candidate_values = _candidate_nutrition_values(
                candidate_data
            )
            if candidate_basis != comparison_basis:
                continue

        if (
            data.product_name
            and product_name.casefold() == data.product_name.casefold()
        ):
            continue

        shared = set(comparable_current) & set(candidate_values)
        if len(shared) < 2:
            continue
        if goal_nutrient is not None and goal_nutrient not in shared:
            continue
        improvements = []
        tradeoffs = []
        for field_name in sorted(shared):
            current_value = comparable_current[field_name]
            alternative_value = candidate_values[field_name]
            better_when = "higher" if field_name in {"fiber_g", "protein_g"} else "lower"
            is_better = (
                alternative_value > current_value
                if better_when == "higher"
                else alternative_value < current_value
            )
            is_worse = (
                alternative_value < current_value
                if better_when == "higher"
                else alternative_value > current_value
            )
            if is_better:
                improvements.append(
                    {
                        "nutrient": field_name,
                        "current_value": current_value,
                        "alternative_value": alternative_value,
                        "unit": (
                            "mg"
                            if field_name == "sodium_mg"
                            else "kcal"
                            if field_name == "energy_kcal"
                            else "g"
                        ),
                        "basis": comparison_basis,
                    }
                )
            elif is_worse:
                tradeoffs.append(
                    {
                        "nutrient": field_name,
                        "current_value": current_value,
                        "alternative_value": alternative_value,
                        "unit": (
                            "mg"
                            if field_name == "sodium_mg"
                            else "kcal"
                            if field_name == "energy_kcal"
                            else "g"
                        ),
                        "basis": comparison_basis,
                    }
                )
        goal_improvements = [
            item for item in improvements
            if item["nutrient"] == goal_nutrient
        ]
        if goal_nutrient is not None and not goal_improvements:
            continue
        if improvements:
            profile_warnings = _candidate_profile_warnings(
                product,
                candidate_data.model_dump(mode="json") if isinstance(product, dict) else None,
                current_user,
            )
            has_profile_factors = _has_profile_factors(current_user)
            available_candidate_values = set(candidate_values)
            missing_nutrients = sorted(
                set(
                    (
                        "energy_kcal",
                        "total_fat_g",
                        "saturated_fat_g",
                        "trans_fat_g",
                        "carbohydrates_g",
                        "sugar_g",
                        "added_sugar_g",
                        "protein_g",
                        "fiber_g",
                        "sodium_mg",
                    )
                )
                - available_candidate_values
            )
            ingredients_available = bool(
                candidate_input.get("ingredients")
                or candidate_input.get("ingredients_text")
            ) if isinstance(product, dict) else bool(
                getattr(product, "ingredients", [])
                or getattr(product, "ingredients_text", None)
            )
            declared_allergens = (
                candidate_input.get("allergens") or []
                if isinstance(product, dict)
                else getattr(product, "declared_allergens", None) or []
            )
            may_contain_declarations = (
                candidate_input.get("may_contain") or []
                if isinstance(product, dict)
                else getattr(product, "may_contain", None) or []
            )
            candidate_source = (
                product.get("source_provenance") or "user_saved_analysis"
                if isinstance(product, dict)
                else {
                    "source_name": getattr(product, "source_name", None),
                    "source_url": getattr(product, "source_url", None),
                    "source_license": getattr(product, "source_license", None),
                }
            )
            if isinstance(candidate_source, dict) and not any(candidate_source.values()):
                candidate_source = "catalog_source_not_recorded"
            goal_current_value = comparable_current.get(goal_nutrient)
            goal_alternative_value = candidate_values.get(goal_nutrient)
            goal_improvement_amount = (
                goal_current_value - goal_alternative_value
                if goal_nutrient in {"sugar_g", "sodium_mg", "saturated_fat_g", "energy_kcal"}
                and goal_current_value is not None
                and goal_alternative_value is not None
                else goal_alternative_value - goal_current_value
                if goal_nutrient in {"protein_g", "fiber_g"}
                and goal_current_value is not None
                and goal_alternative_value is not None
                else 0
            )
            comparison_details = [
                {
                    "nutrient": field_name,
                    "current_value": comparable_current[field_name],
                    "alternative_value": candidate_values[field_name],
                    "unit": (
                        "mg"
                        if field_name == "sodium_mg"
                        else "kcal"
                        if field_name == "energy_kcal"
                        else "g"
                    ),
                    "basis": comparison_basis,
                    "direction": (
                        "higher_is_preferred"
                        if field_name in {"fiber_g", "protein_g"}
                        else "lower_is_preferred"
                    ),
                }
                for field_name in sorted(shared)
            ]
            ranking_key = (
                any(item["type"] == "potential_conflict" for item in profile_warnings),
                sum(item["type"] == "needs_review" for item in profile_warnings),
                -goal_improvement_amount if goal_nutrient else -len(improvements),
                len(tradeoffs),
                len(missing_nutrients),
                product_name.casefold(),
            )
            selection_reasons = [
                (
                    f"Compared on {goal_nutrient.replace('_g', '').replace('_mg', '').replace('_kcal', '')}: "
                    f"{goal_alternative_value} versus {goal_current_value} {_REC_NUTRIENT_UNITS.get(goal_nutrient, 'g')} "
                    f"per 100 {comparison_basis.removeprefix('per_100')}."
                    if goal_nutrient
                    else f"Improves {len(improvements)} of {len(shared)} shared label values without an aggregate health score."
                ),
                (
                    "An ingredient list is available."
                    if ingredients_available
                    else "Ingredient list is missing; ingredient transparency could not be assessed."
                ),
            ]
            if tradeoffs:
                selection_reasons.append(
                    f"{len(tradeoffs)} nutritional trade-off(s) are listed."
                )
            if missing_nutrients:
                selection_reasons.append(
                    f"Missing candidate nutrient values: {', '.join(missing_nutrients)}."
                )
            recommendations.append(
                {
                    "product": product_name,
                    "brand": (
                        product.get("brand")
                        if isinstance(product, dict)
                        else product.brand
                    ),
                    "improvements": improvements,
                    "tradeoffs": tradeoffs,
                    "compared_nutrients": sorted(shared),
                    "nutritional_values_considered": comparison_details,
                    "selection_reasons": selection_reasons,
                    "ingredient_transparency": {
                        "ingredient_list": (
                            "provided" if ingredients_available else "not_provided"
                        ),
                        "declared_allergens": (
                            "provided"
                            if (
                                candidate_input.get("allergens") is not None
                                if isinstance(product, dict)
                                else getattr(product, "declared_allergens", None) is not None
                            )
                            else "not_provided"
                        ),
                        "may_contain": (
                            "provided"
                            if (
                                candidate_input.get("may_contain") is not None
                                if isinstance(product, dict)
                                else getattr(product, "may_contain", None) is not None
                            )
                            else "not_provided"
                        ),
                        "meaning": "Field availability only; it is not an ingredient safety or completeness determination.",
                    },
                    "allergen_declarations": {
                        "declared": declared_allergens,
                        "may_contain": may_contain_declarations,
                    },
                    "source_provenance": candidate_source,
                    "recommendation_goal": effective_goal,
                    "requested_goal": data.recommendation_goal,
                    "profile_compatibility": (
                        "POTENTIAL_CONFLICT"
                        if any(item["type"] == "potential_conflict" for item in profile_warnings)
                        else "NEEDS_REVIEW"
                        if profile_warnings
                        else "NO_CONFLICT_FOUND"
                        if has_profile_factors
                        else "NOT_EVALUATED"
                    ),
                    "profile_warnings": profile_warnings,
                    "profile_limitation": (
                        "No text conflict found is not a safety or suitability conclusion; review full labels and unassessed profile factors."
                        if current_user is not None
                        else "No authenticated profile was used to assess this candidate."
                    ),
                    "data_completeness": {
                        "shared_nutrient_count": len(shared),
                        "missing_nutrients": missing_nutrients,
                        "unknown_values_are_not_estimated": True,
                    },
                    "reason": (
                        (
                            f"This stored product improves the {effective_goal.replace('_', ' ')} comparison target; "
                            if goal_nutrient is not None
                            else "This stored product improves at least one shared nutrient; "
                        )
                        + "review the listed trade-offs, missing fields, and full label."
                    ),
                    "limitation": (
                        "This is a nutrient comparison, not a medical, safety, "
                        "or overall-health recommendation."
                    ),
                    "_ranking_key": ranking_key,
                }
            )
    recommendations.sort(
        key=lambda item: item["_ranking_key"]
    )
    if not recommendations:
        return {
            "status": "NOT_AVAILABLE",
            "items": [],
            "reason": (
                "No stored products had at least two comparable nutrient values "
                "and an improvement for the selected comparison goal."
            ),
        }
    return {
        "status": "POTENTIAL_ALTERNATIVES",
        "items": [
            {key: value for key, value in item.items() if key != "_ranking_key"}
            for item in recommendations[:3]
        ],
        "reason": "Candidates use only actual stored product nutrient values.",
        "comparison_basis": comparison_basis,
        "recommendation_goal": effective_goal,
        "requested_goal": data.recommendation_goal,
        "ranking_method": (
            "Candidates are ranked by profile conflicts and review needs, then "
            "selected-goal improvement (or distinct improvements for balanced), "
            "trade-offs, missing nutrients, and product name. No aggregate food-quality score is used."
        ),
    }


def _has_profile_factors(user) -> bool:
    if user is None:
        return False
    profile = getattr(user, "health_profile", None)
    return bool(
        getattr(profile, "dietary_preferences", None)
        or getattr(profile, "ingredient_exclusions", None)
        or getattr(profile, "nutrition_goals", None)
        or getattr(profile, "calorie_goal_kcal", None)
        or getattr(profile, "protein_goal_g", None)
        or getattr(user, "allergen_selections", [])
        or getattr(user, "health_condition_selections", [])
    )


def _candidate_profile_warnings(product, candidate_input, user) -> list[dict]:
    if not _has_profile_factors(user):
        return []
    profile = getattr(user, "health_profile", None)
    ingredient_exclusions = getattr(profile, "ingredient_exclusions", None) or []
    preferences = getattr(profile, "dietary_preferences", None) or []
    nutrition_goals = getattr(profile, "nutrition_goals", None) or []
    calorie_goal = getattr(profile, "calorie_goal_kcal", None)
    protein_goal = getattr(profile, "protein_goal_g", None)
    ingredient_texts = []
    declaration_texts = []
    if candidate_input:
        ingredient_texts = list(candidate_input.get("ingredients") or [])
        if candidate_input.get("ingredients_text"):
            ingredient_texts.extend(
                split_ingredients_text(candidate_input["ingredients_text"])
            )
        for key in ("allergens", "may_contain"):
            values = candidate_input.get(key)
            if isinstance(values, list):
                declaration_texts.extend(str(value) for value in values)
            elif isinstance(values, str) and values:
                declaration_texts.append(values)
    elif not isinstance(product, dict):
        ingredient_texts = [
            item.original_label_text
            for item in getattr(product, "ingredients", [])
            if item.original_label_text
        ]
        if getattr(product, "ingredients_text", None):
            ingredient_texts.extend(
                split_ingredients_text(product.ingredients_text)
            )
        declaration_texts.extend(
            getattr(product, "declared_allergens", None) or []
        )
        declaration_texts.extend(
            getattr(product, "may_contain", None) or []
        )

    warnings = []
    allergen_names = [
        selection.allergen.name
        if selection.allergen is not None
        else selection.custom_allergen_name
        for selection in getattr(user, "allergen_selections", [])
    ]
    for allergen in filter(None, allergen_names):
        matches = [
            item
            for item in [*ingredient_texts, *declaration_texts]
            if match_allergen_text(allergen, item)
        ]
        if matches:
            warnings.append(
                {
                    "type": "potential_conflict",
                    "factor": f"allergen:{allergen}",
                    "matched_label_text": matches,
                }
            )
        else:
            warnings.append(
                {
                    "type": "needs_review",
                    "factor": f"allergen:{allergen}",
                    "matched_label_text": [],
                    "note": "No text match does not establish allergen absence.",
                }
            )

    for exclusion in ingredient_exclusions:
        matches = [
            item for item in ingredient_texts
            if re.search(
                rf"(?<!\w){re.escape(exclusion.casefold())}(?!\w)",
                item.casefold(),
            )
        ]
        if matches:
            warnings.append(
                {
                    "type": "potential_conflict",
                    "factor": f"ingredient_exclusion:{exclusion}",
                    "matched_label_text": matches,
                }
            )
        else:
            warnings.append(
                {
                    "type": "needs_review",
                    "factor": f"ingredient_exclusion:{exclusion}",
                    "matched_label_text": [],
                    "note": "No text match does not establish ingredient absence.",
                }
            )
    confirmed_label = bool(
        candidate_input and candidate_input.get("corrections_confirmed")
    )
    symbol_review = (
        candidate_input.get("symbol_review") if confirmed_label else None
    )
    candidate_text = (
        " ".join(
            str(candidate_input.get(key, ""))
            for key in ("label_text", "ingredients_text")
        ).casefold()
        if candidate_input
        else ""
    )
    for preference in preferences:
        normalized = preference.casefold()
        conflict = (
            normalized in {"vegetarian", "vegan"}
            and symbol_review == "NON_VEGETARIAN"
        ) or (
            normalized == "vegan"
            and re.search(r"\bnon[\s-]?vegan\b", candidate_text)
        )
        matched = (
            normalized == "vegetarian"
            and symbol_review == "VEGETARIAN"
        ) or (
            normalized == "vegan"
            and confirmed_label
            and re.search(r"\bvegan\b", candidate_text)
            and not re.search(r"\bnon[\s-]?vegan\b", candidate_text)
        )
        if conflict:
            warnings.append(
                {
                    "type": "potential_conflict",
                    "factor": f"dietary_preference:{preference}",
                    "matched_label_text": [
                        "confirmed non-vegetarian symbol review"
                        if symbol_review == "NON_VEGETARIAN"
                        else "confirmed non-vegan declaration"
                    ],
                }
            )
        elif not matched:
            warnings.append(
                {
                    "type": "needs_review",
                    "factor": f"dietary_preference:{preference}",
                    "matched_label_text": [],
                    "note": "The stored candidate does not include confirmed supporting declaration evidence.",
                }
            )
    for selection in getattr(user, "health_condition_selections", []):
        if selection.condition is not None:
            warnings.append(
                {
                    "type": "needs_review",
                    "factor": f"health_condition:{selection.condition.name}",
                    "matched_label_text": [],
                    "note": "Alternative recommendations are not condition-specific.",
                }
            )
    if nutrition_goals:
        warnings.append(
            {
                "type": "needs_review",
                "factor": "nutrition_goals",
                "matched_label_text": [],
                "note": "Review the comparison goal and all trade-offs; no full goal-profile suitability evaluation is claimed.",
            }
        )
    if calorie_goal or protein_goal:
        warnings.append(
            {
                "type": "needs_review",
                "factor": "daily_nutrition_targets",
                "matched_label_text": [],
                "note": "Per-serving contributions are descriptive and do not determine daily-goal suitability.",
            }
        )
    return warnings


def _ingredient_items(data: ProductAnalysisInput) -> list[str] | None:
    if data.ingredients is not None:
        return list(data.ingredients)
    if data.ingredients_text is not None:
        return split_ingredients_text(data.ingredients_text)
    return None


def _allergen_status(
    canonical_name: str,
    knowledge_records: list[dict] | None,
) -> str:
    for record in knowledge_records or []:
        if (
            record.get("__allergen_catalog__")
            and record.get("canonical_name", "").casefold()
            == canonical_name.casefold()
        ):
            return record.get("verification_status", "REVIEW_REQUIRED")
    return "REVIEW_REQUIRED"


def _allergen_matches(
    texts: Sequence[str] | None,
    *,
    source: str,
    knowledge_records: list[dict] | None,
) -> list[dict]:
    records = knowledge_records or []
    if not any(record.get("__allergen_catalog__") for record in records):
        from app.data.ingredient_knowledge import get_curated_ingredient_records

        records = [
            *records,
            *(
                record
                for record in get_curated_ingredient_records()
                if record.get("__allergen_catalog__")
            ),
        ]
    matches = []
    seen = set()
    for text in texts or []:
        for record in records:
            if not record.get("__allergen_catalog__"):
                continue
            canonical_name = record["canonical_name"]
            matched_alias = match_allergen_text(
                canonical_name,
                text,
                knowledge_records=records,
            )
            key = (canonical_name.casefold(), source, text.casefold())
            if matched_alias and key not in seen:
                seen.add(key)
                matches.append(
                    {
                        "allergen": canonical_name,
                        "matched_text": text,
                        "matched_alias": matched_alias,
                        "source": source,
                        "verification_status": _allergen_status(
                            canonical_name,
                            records,
                        ),
                        "interpretation": (
                            "Label text match only; it does not establish "
                            "presence, absence, exposure, or individual "
                            "suitability."
                        ),
                    }
                )
    return matches


def _declaration_section(
    declarations: Sequence[str] | None,
    *,
    source: str,
    knowledge_records: list[dict] | None,
) -> dict:
    return {
        "status": "provided" if declarations else "not_provided",
        "label_text": list(declarations or []),
        "matches": _allergen_matches(
            declarations,
            source=source,
            knowledge_records=knowledge_records,
        ),
        "note": (
            "A listed declaration is reported separately from ingredients; "
            "a missing or unmatched declaration does not establish allergen absence."
        ),
    }


def analyze_product(
    data: ProductAnalysisInput,
    *,
    knowledge_records: list[dict] | None = None,
    current_user=None,
    stored_products: Sequence = (),
) -> dict:
    general = analyze_label(data, knowledge_records=knowledge_records)
    ingredient_items = _ingredient_items(data)
    ingredients_available = (
        data.ingredients is not None or data.ingredients_text is not None
    )
    ingredient_analysis = general["ingredient_analysis"]
    additive_analysis = detect_additives(ingredient_items)

    ingredient_verification = [
        {
            "label_text": item["original_label_text"],
            "matched_name": item["matched_name"],
            "verification_status": item.get("verification_status", "UNVERIFIED"),
            "match_quality": item["match_quality"],
        }
        for item in ingredient_analysis["ingredients"]
    ]
    additive_verification = [
        {
            "name": item["name"],
            "verification_status": item["verification_status"],
        }
        for item in additive_analysis["matched_additives"]
    ]
    ingredient_matches = _allergen_matches(
        ingredient_items,
        source="ingredient",
        knowledge_records=knowledge_records,
    )
    declared = _declaration_section(
        data.allergens,
        source="declared_allergen",
        knowledge_records=knowledge_records,
    )
    may_contain = _declaration_section(
        data.may_contain,
        source="may_contain",
        knowledge_records=knowledge_records,
    )

    missing_fields = []
    for field, available in (
        ("nutrient_basis", bool(data.basis)),
        ("ingredients", ingredients_available),
        ("allergen_declarations", bool(data.allergens)),
        ("may_contain_declaration", bool(data.may_contain)),
    ):
        if not available:
            missing_fields.append(field)
    missing_fields.extend(
        f"nutrients.{name}"
        for name, value in (
            ("sugar_g", data.sugar_g),
            ("added_sugar_g", data.added_sugar_g),
            ("sodium_mg", data.sodium_mg),
            ("saturated_fat_g", data.saturated_fat_g),
        )
        if value is None
    )
    health_score = general["health_score"]
    profile_result = (
        analyze_personalized_label(
            current_user,
            data,
            knowledge_records=knowledge_records,
        )
        if current_user is not None
        else None
    )
    nutrition_intelligence = build_nutrition_intelligence(
        data,
        excess_nutrients=general["excess_nutrients"],
    )
    food_personal_suitability = evaluate_product_suitability(
        user=current_user,
        data=data,
        intelligence=nutrition_intelligence,
        legacy_profile_analysis=profile_result,
    )
    food_scores = build_food_scores(
        nutrition_intelligence,
        data=data,
        personalized_suitability=food_personal_suitability,
    )
    if profile_result is None:
        personal_suitability = {
            "status": "NOT_EVALUATED",
            "reason": "No authenticated personal profile was used.",
        }
    elif profile_result["personal_suitability"]["status"] == "unknown":
        personal_suitability = {
            "status": "INSUFFICIENT_DATA",
            "details": profile_result["personal_suitability"],
        }
    elif profile_result["personal_suitability"]["status"] == "no_profile_factors":
        personal_suitability = {
            "status": "NOT_EVALUATED",
            "reason": "The authenticated profile has no configured conditions or allergens.",
            "details": profile_result["personal_suitability"],
        }
    elif profile_result["personal_suitability"]["detected_concerns"]:
        personal_suitability = {
            "status": "UNSUITABLE",
            "details": profile_result["personal_suitability"],
        }
    elif profile_result["personal_suitability"]["warnings"]:
        personal_suitability = {
            "status": "CAUTION",
            "details": profile_result["personal_suitability"],
        }
    else:
        personal_suitability = {
            "status": "SUITABLE",
            "details": profile_result["personal_suitability"],
            "reason": (
                "No supported match was found in the submitted text. "
                "This does not establish safety or allergen absence."
            ),
        }

    completeness = {
        "status": "complete_for_submitted_fields" if not missing_fields else "partial",
        "provided_fields": [
            field
            for field, available in (
                ("product_name", bool(data.product_name)),
                ("nutrient_basis", bool(data.basis)),
                ("ingredients", ingredients_available),
                ("allergen_declarations", bool(data.allergens)),
                ("may_contain_declaration", bool(data.may_contain)),
            )
            if available
        ],
        "missing_fields": missing_fields,
        "health_score_data": health_score["data_completeness"],
        "limitations": [
            "Analysis uses submitted label text and values; it does not verify the physical package.",
            "Ingredient and additive matching does not infer concentration, quantity, or exposure.",
            "A missing or unmatched ingredient/allergen is not evidence of absence or safety.",
            "The health score uses only the existing project-configured nutrient method and is not an official grade or medical advice.",
            *(
                ["No authenticated personal profile was used."]
                if current_user is None
                else ["Personal analysis is limited to the supported profile rules."]
            ),
            (
                "Only actual catalog products and this user's saved reports were considered for alternatives."
                if current_user is not None
                else "Only actual catalog products were considered for alternatives."
            ),
        ],
    }
    summary = (
        "Label-only informational analysis; no medical or safety conclusion is made."
    )
    if data.explanation_level == "detailed":
        summary += (
            f" {health_score['data_completeness']['text']}; "
            f"{len(ingredient_verification)} ingredient matches and "
            f"{len(additive_verification)} additive matches have explicit "
            "verification statuses."
        )

    return {
        "product": {"name": data.product_name},
        "nutrition": {
            "basis": general["basis"],
            "excess_nutrients": general["excess_nutrients"],
            "health_score": health_score,
            "additional_nutrients": {
                name: nutrient.model_dump()
                for name, nutrient in data.additional_nutrients.items()
                if nutrient.value is not None
            },
            "method_note": general["note"],
        },
        "ingredients": {
            "text": data.ingredients_text,
            "analysis": ingredient_analysis,
            "additive_analysis": additive_analysis,
            "verification_statuses": {
                "ingredients": ingredient_verification,
                "additives": additive_verification,
            },
        },
        "allergen_analysis": {
            "ingredient_matches": ingredient_matches,
            "declared_allergens": declared,
            "may_contain": may_contain,
            "personal_suitability": personal_suitability,
        },
        "personalized_suitability": personal_suitability,
        "alternatives": _report_alternatives(
            data,
            stored_products,
            current_user=current_user,
        ),
        "food_intelligence": {
            "nutrition": nutrition_intelligence,
            "scores": food_scores,
            "personal_suitability": food_personal_suitability,
        },
        "completeness": completeness,
        "explanation_level": data.explanation_level,
        "summary": summary,
        "note": (
            "Informational label analysis only; not medical advice, a "
            "regulatory or official grade, or a product safety determination."
        ),
    }


def answer_product_question(
    question: str,
    context: dict[str, Any],
    *,
    explanation_level: str = "standard",
) -> dict:
    """Answer only a small set of factual questions from submitted report data."""
    normalized = re.sub(r"\s+", " ", question.casefold()).strip()

    def response(intent: str, status: str, answer: str, evidence: Any = None) -> dict:
        if explanation_level == "detailed":
            answer = (
                f"{answer} This deterministic response uses only the supplied "
                "report context and does not consult external evidence."
            )
        result = {
            "intent": intent,
            "status": status,
            "answer": answer,
            "limitations": [
                "Answers are grounded only in the report context submitted with this request.",
                "No LLM provider or external source is used.",
                "This is not medical advice or a product safety determination.",
            ],
            "context_scope": (
                "The answer distinguishes submitted product facts from general "
                "catalog information."
            ),
            "response_mode": "DETERMINISTIC_FALLBACK",
            "provider_status": "NO_GENERATIVE_PROVIDER_CONFIGURED",
            "explanation_level": explanation_level,
        }
        if evidence is not None:
            result["evidence"] = evidence
        return result

    if re.search(r"\b(alternative|substitute|similar product|recommend|compare|comparison)\b", normalized):
        alternatives = context.get("alternatives")
        if not isinstance(alternatives, dict):
            alternatives = {"status": "NOT_AVAILABLE"}
        items = alternatives.get("items") or []
        if items:
            return response(
                "alternatives",
                "answered",
                "These stored products have better values for at least one shared nutrient. Review the comparisons, trade-offs, and full product labels.",
                items,
            )
        return response(
            "alternatives",
            "unknown",
            "No comparable stored products were queried, so alternatives are not available.",
            alternatives,
        )

    suitability_terms = re.search(
        r"\b(profile|personal suitability|suitable|my condition|"
        r"diabetes|hypertension|heart disease|celiac|pku|kidney disease|"
        r"ibs|gout)\b",
        normalized,
    )
    if suitability_terms:
        allergen_context = context.get("allergen_analysis")
        if not isinstance(allergen_context, dict):
            allergen_context = {}
        food_intelligence = context.get("food_intelligence")
        if not isinstance(food_intelligence, dict):
            food_intelligence = {}
        suitability = (
            (food_intelligence.get("personal_suitability") or {})
            or context.get("personalized_suitability")
            or allergen_context.get(
            "personal_suitability"
            )
        )
        if not isinstance(suitability, dict):
            suitability = {"status": "NOT_EVALUATED"}
        status = suitability.get("status", "NOT_EVALUATED")
        if status in {
            "UNSUITABLE",
            "CAUTION",
            "SUITABLE",
            "UNSUITABLE_BASED_ON_USER_PREFERENCES",
            "POTENTIAL_CONFLICT",
            "NEEDS_REVIEW",
            "SUITABLE_BASED_ON_AVAILABLE_DATA",
        }:
            return response(
                "personal_suitability",
                "answered",
                f"The available profile rules returned {status}. This is a limited label-text assessment, not medical advice or a clinical suitability decision.",
                suitability,
            )
        return response(
            "personal_suitability",
            "unknown",
            "This product's personal suitability was not established. The analysis may lack an authenticated profile, required label information, or a supported rule for this condition; this is not medical advice.",
            suitability,
        )

    if re.search(
        r"\b(safe|safety|healthy|should i eat|medical|diagnos|illness|disease|cure)\b",
        normalized,
    ):
        return response(
            "safety_or_medical",
            "unknown",
            "The submitted label context cannot determine whether this product is safe or medically suitable. This service does not provide medical advice.",
        )

    allergen_analysis = context.get("allergen_analysis")
    if not isinstance(allergen_analysis, dict):
        allergen_analysis = {}
    if re.search(r"\b(allergen|allergy|may contain|contains|peanut|milk|dairy|gluten|soy|sesame|egg|fish|nut)\b", normalized):
        declared = allergen_analysis.get("declared_allergens", {})
        may_contain = allergen_analysis.get("may_contain", {})
        if not isinstance(declared, dict):
            declared = {}
        if not isinstance(may_contain, dict):
            may_contain = {}
        evidence = {
            "declared_allergens": declared.get("label_text"),
            "declared_matches": declared.get("matches", []),
            "may_contain": may_contain.get("label_text"),
            "may_contain_matches": may_contain.get("matches", []),
        }
        if not any(
            evidence[key]
            for key in ("declared_allergens", "declared_matches", "may_contain", "may_contain_matches")
        ):
            return response(
                "allergens",
                "unknown",
                "Allergen declaration and may-contain text were not available in the submitted context; absence cannot be inferred.",
                evidence,
            )
        return response(
            "allergens",
            "answered",
            "The submitted declared-allergen text and precautionary may-contain text are reported separately below. A label-text match does not establish personal suitability.",
            evidence,
        )

    ingredients = context.get("ingredients")
    asked_ingredient = re.search(
        r"\b(?:what is|what does|explain|meaning of)\s+(?:the\s+)?([a-z][a-z0-9 -]{1,60}?)(?:\?|$)",
        normalized,
    )
    if asked_ingredient and isinstance(ingredients, dict):
        analysis = ingredients.get("analysis")
        entries = analysis.get("ingredients", []) if isinstance(analysis, dict) else []
        phrase = asked_ingredient.group(1).strip()
        matched = [
            item
            for item in entries
            if isinstance(item, dict)
            and phrase in " ".join(
                str(item.get(key, ""))
                for key in ("original_label_text", "matched_name", "normalized_name")
            ).casefold()
        ]
        if matched:
            return response(
                "ingredient_explanation",
                "answered",
                "Here is the matching ingredient information included in the submitted analysis. Its presence does not establish amount, exposure, or safety.",
                matched,
            )

    additive_code = re.search(r"\b(?:ins|e)[ -]?(\d{3,4}[a-z]?)\b", normalized)
    if additive_code:
        from app.services.additive_detector import CURATED_ADDITIVES

        wanted = additive_code.group(1).casefold()
        normalized_wanted = re.sub(r"[^a-z0-9]", "", wanted)
        wanted_e_number = "e" + normalized_wanted
        match = next(
            (
                item
                for item in CURATED_ADDITIVES
                if re.sub(r"[^a-z0-9]", "", str(item.get("ins", "")).casefold())
                == normalized_wanted
                or re.sub(r"[^a-z0-9]", "", str(item.get("e_number", "")).casefold())
                == wanted_e_number
            ),
            None,
        )
        if match is None:
            return response(
                "additive_code",
                "unknown",
                "That additive code was not found in the current catalog. No identity or function is inferred.",
            )
        return response(
            "additive_code",
            "answered",
            "This is general catalog information; it does not establish that the additive is present in the submitted product.",
            {
                "name": match.get("name"),
                "ins": match.get("ins"),
                "e_number": match.get("e_number"),
                "function": match.get("purpose"),
                "verification_status": match.get("verification_status"),
            },
        )

    food_intelligence = context.get("food_intelligence")
    if not isinstance(food_intelligence, dict):
        food_intelligence = {}
    food_scores = food_intelligence.get("scores", {})
    if re.search(r"\b(strengths?|best parts?|highlights?)\b", normalized):
        scores = food_scores.get("scores") if isinstance(food_scores, dict) else None
        if not isinstance(scores, dict):
            return response(
                "product_strengths",
                "unknown",
                "No food-intelligence scores were included in the submitted report context.",
            )
        available = {
            name: item
            for name, item in scores.items()
            if isinstance(item, dict) and item.get("score") is not None
        }
        if not available:
            return response(
                "product_strengths",
                "unknown",
                "The submitted report does not include enough data to identify score indicators.",
                scores,
            )
        return response(
            "product_strengths",
            "answered",
            "These are the available project-defined score indicators. They describe only the supplied label data and are not an overall health or safety judgement.",
            available,
        )

    ingredients = context.get("ingredients")
    if re.search(r"\b(additive|preservative|ingredient|verification)\b", normalized):
        if isinstance(ingredients, dict):
            if "additive" in normalized or "preservative" in normalized:
                evidence = ingredients.get("additive_analysis")
                key = "additives"
            elif "verification" in normalized:
                evidence = ingredients.get("verification_statuses")
                key = "verification_statuses"
            else:
                evidence = ingredients.get("analysis")
                key = "ingredient_analysis"
        else:
            evidence = None
            key = "ingredients"
        if evidence is None:
            return response(
                key,
                "unknown",
                "The submitted context does not include analyzed ingredient or additive results.",
            )
        return response(
            key,
            "answered",
            "Here are the matching results from the submitted context. Additive/ingredient matching does not estimate concentration or exposure.",
            evidence,
        )

    nutrition = context.get("nutrition")
    if re.search(
        r"\b(nutrition|score|sugar|sodium|salt|fat|nutrient|protein|"
        r"fiber|fibre|energy|calories|carbohydrates|carbs)\b",
        normalized,
    ):
        if not isinstance(nutrition, dict):
            return response(
                "nutrition",
                "unknown",
                "Analyzed nutrition values and the project health score were not available in the submitted context.",
            )
        evidence = {
            "basis": nutrition.get("basis"),
            "excess_nutrients": nutrition.get("excess_nutrients"),
            "health_score": nutrition.get("health_score"),
            "food_intelligence": food_intelligence.get("nutrition"),
            "food_scores": food_scores.get("scores")
            if isinstance(food_scores, dict)
            else None,
        }
        if all(value is None for value in evidence.values()):
            return response(
                "nutrition",
                "unknown",
                "Analyzed nutrition values and the project health score were not available in the submitted context.",
                evidence,
            )
        return response(
            "nutrition",
            "answered",
            "These are the submitted label's analyzed nutrient assessments and existing project health score; the score is not an official grade or medical advice.",
            evidence,
        )

    if re.search(r"\b(product name|product called|name of (?:this )?product)\b", normalized):
        product = context.get("product")
        name = product.get("name") if isinstance(product, dict) else context.get("product_name")
        if not name:
            return response("product_name", "unknown", "A product name was not provided in the submitted context.")
        return response("product_name", "answered", f"The submitted product name is {name}.", {"name": name})

    if re.search(r"\b(limitation|limitations|confidence|data completeness)\b", normalized):
        limitations = context.get("limitations") or context.get("completeness")
        if limitations is None:
            return response(
                "limitations",
                "unknown",
                "No limitations or completeness details were included in the submitted report context.",
            )
        return response(
            "limitations",
            "answered",
            "These limitations describe missing inputs and boundaries of the submitted analysis.",
            limitations,
        )

    return response(
        "unsupported",
        "unknown",
        "I can answer from the supplied product name, nutrition, matched ingredients/additives, allergen declarations, profile assessment, score indicators, and stored alternatives. Other information is not inferred.",
    )
