from typing import Any

from pydantic import ValidationError

from app.schemas.product_analysis import ProductAnalysisInput
from app.services.nutrition_intelligence import build_nutrition_intelligence

_COMPARISON_FIELDS = (
    "energy",
    "total_fat",
    "saturated_fat",
    "trans_fat",
    "carbohydrates",
    "sugar",
    "added_sugar",
    "protein",
    "fiber",
    "sodium",
)

_GOAL_FIELDS = {
    "lower_sugar": ("sugar", "lower"),
    "lower_sodium": ("sodium", "lower"),
    "lower_saturated_fat": ("saturated_fat", "lower"),
    "higher_protein": ("protein", "higher"),
    "higher_fiber": ("fiber", "higher"),
    "lower_calories": ("energy", "lower"),
}
_NUTRIENT_DIRECTIONS = {
    "energy": "lower",
    "total_fat": "lower",
    "saturated_fat": "lower",
    "trans_fat": "lower",
    "sugar": "lower",
    "added_sugar": "lower",
    "protein": "higher",
    "fiber": "higher",
    "sodium": "lower",
}


def compare_saved_product_reports(
    reports: list[dict[str, Any]],
    *,
    recommendation_goal: str = "balanced",
) -> dict:
    rows = []
    for report in reports:
        analysis_data = report.get("analysis_data") or {}
        product_report = analysis_data.get("product_report") or {}
        input_data = analysis_data.get("input") or {}
        try:
            data = ProductAnalysisInput.model_validate(input_data)
        except ValidationError as error:
            raise ValueError("A saved product report contains invalid analysis data.") from error
        intelligence = build_nutrition_intelligence(data)
        indicators = (
            (product_report.get("food_intelligence") or {})
            .get("scores", {})
            .get("scores", {})
        )
        suitability = (
            product_report.get("food_intelligence") or {}
        ).get("personal_suitability")
        ingredients = product_report.get("ingredients") or {}
        allergen_analysis = product_report.get("allergen_analysis") or {}
        ingredient_text_available = bool(
            data.ingredients
            or data.ingredients_text
            or ingredients.get("text")
        )
        declared = allergen_analysis.get("declared_allergens") or {}
        may_contain = allergen_analysis.get("may_contain") or {}
        nutrition_values = intelligence["nutrient_density_per_100"]
        missing_fields = sorted(
            set(_COMPARISON_FIELDS) - set(nutrition_values)
        )
        rows.append(
            {
                "scan_id": report["scan_id"],
                "product_name": (
                    input_data.get("product_name")
                    or (product_report.get("product") or {}).get("name")
                    or "Unnamed product"
                ),
                "reported_basis": intelligence["reported_basis"],
                "comparison_basis": intelligence["normalized_basis"],
                "nutrients": intelligence["nutrient_density_per_100"],
                "per_serving": intelligence["per_serving"],
                "serving_size": data.serving_size_text,
                "normalization": (
                    "Per-serving label values were normalized using the stated metric serving size."
                    if data.basis == "per_serving"
                    and intelligence["normalized_basis"] is not None
                    else "Only reported values on a compatible per-100 basis are compared."
                ),
                "ingredient_transparency": {
                    "ingredient_list": (
                        "provided" if ingredient_text_available else "not_provided"
                    ),
                    "declared_allergens": (
                        declared.get("status", "not_provided")
                    ),
                    "may_contain": may_contain.get("status", "not_provided"),
                    "score": indicators.get("ingredient_transparency"),
                    "meaning": "Declaration availability only; it is not an ingredient safety or completeness determination.",
                },
                "allergens": {
                    "declared": declared.get("label_text", data.allergens or []),
                    "may_contain": may_contain.get(
                        "label_text",
                        data.may_contain or [],
                    ),
                },
                "indicators": {
                    "nutrition_quality": indicators.get("nutrition_quality"),
                    "personal_suitability": suitability,
                    "limitation": "Indicators are separate project measures; none is a universal product-quality score.",
                },
                "data_completeness": {
                    "available_nutrients": sorted(nutrition_values),
                    "missing_nutrients": missing_fields,
                    "missing_or_unusable_fields": intelligence[
                        "missing_or_unusable_fields"
                    ],
                },
                "advantages": [],
                "tradeoffs": [],
            }
        )

    bases = {row["comparison_basis"] for row in rows}
    basis = next(iter(bases)) if len(bases) == 1 else None
    common = set(_COMPARISON_FIELDS)
    if basis is None:
        common.clear()
    else:
        common.intersection_update(
            *(set(row["nutrients"]) for row in rows)
        )
    comparisons = {
        field: {
            "unit": rows[0]["nutrients"][field]["unit"],
            "basis": basis,
            "goal_direction": (
                _GOAL_FIELDS[recommendation_goal][1]
                if recommendation_goal in _GOAL_FIELDS
                and _GOAL_FIELDS[recommendation_goal][0] == field
                else None
            ),
            "values": [
                {
                    "scan_id": row["scan_id"],
                    "product_name": row["product_name"],
                    "value": row["nutrients"][field]["value"],
                }
                for row in rows
            ],
        }
        for field in sorted(common)
    }
    goal_field, goal_direction = _GOAL_FIELDS.get(
        recommendation_goal,
        (None, None),
    )
    goal_comparison = comparisons.get(goal_field) if goal_field else None
    if goal_comparison:
        target_values = [
            item["value"] for item in goal_comparison["values"]
        ]
        best_value = (
            max(target_values)
            if goal_direction == "higher"
            else min(target_values)
        )
        worst_value = (
            min(target_values)
            if goal_direction == "higher"
            else max(target_values)
        )
        for row in rows:
            row_value = row["nutrients"][goal_field]["value"]
            if row_value == best_value and best_value != worst_value:
                row["advantages"].append(
                    {
                        "goal": recommendation_goal,
                        "nutrient": goal_field,
                        "value": row_value,
                        "unit": goal_comparison["unit"],
                        "basis": basis,
                        "explanation": "Best reported value among the selected products for the chosen comparison goal.",
                    }
                )
            if row_value == worst_value and len(rows) > 1:
                row["tradeoffs"].append(
                    {
                        "goal": recommendation_goal,
                        "nutrient": goal_field,
                        "value": row_value,
                        "unit": goal_comparison["unit"],
                        "basis": basis,
                        "explanation": "Least favorable reported value among the selected products for the chosen comparison goal.",
                    }
                )
        for field, nutrient_comparison in comparisons.items():
            if field == goal_field or field not in _NUTRIENT_DIRECTIONS:
                continue
            values = [item["value"] for item in nutrient_comparison["values"]]
            direction = _NUTRIENT_DIRECTIONS[field]
            favorable_value = max(values) if direction == "higher" else min(values)
            unfavorable_value = min(values) if direction == "higher" else max(values)
            for row in rows:
                row_value = row["nutrients"].get(field, {}).get("value")
                if row_value == favorable_value and favorable_value != unfavorable_value:
                    row["advantages"].append(
                        {
                            "nutrient": field,
                            "value": row_value,
                            "unit": nutrient_comparison["unit"],
                            "basis": basis,
                            "explanation": "More favorable reported value among the selected products; this is descriptive and separate from the selected goal.",
                        }
                    )
                if row_value == unfavorable_value and favorable_value != unfavorable_value:
                    row["tradeoffs"].append(
                        {
                            "nutrient": field,
                            "value": row_value,
                            "unit": nutrient_comparison["unit"],
                            "basis": basis,
                            "explanation": "Less favorable reported value among the selected products; review it as a trade-off, not an overall product judgment.",
                        }
                    )
    for row in rows:
        row["goal_assessment"] = (
            {
                "status": "COMPARABLE",
                "goal": recommendation_goal,
                "nutrient": goal_field,
                "direction": goal_direction,
            }
            if goal_comparison
            else {
                "status": "NOT_COMPARABLE",
                "goal": recommendation_goal,
                "nutrient": goal_field,
                "reason": (
                    "The selected goal value is missing or the products do not share a compatible normalized basis."
                    if goal_field
                    else "Balanced mode does not label a universal winner."
                ),
            }
        )
    return {
        "status": "COMPARABLE" if comparisons else "INSUFFICIENT_DATA",
        "comparison_basis": basis,
        "recommendation_goal": recommendation_goal,
        "goal_field": goal_field,
        "products": rows,
        "nutrient_comparisons": comparisons,
        "limitations": [
            "Only saved reports belonging to the authenticated user are included.",
            "Values are compared only when they can be normalized to the same per-100 g or per-100 ml basis and recognized units.",
            "Per-serving values are shown separately when conversion to a stated metric serving size is not possible.",
            "Advantages and trade-offs are relative only to the selected goal; balanced mode never declares a universal winner.",
            "Nutrition Quality and Personal Suitability remain separate measures and are not combined into one score.",
            "No medical, safety, or health recommendation is generated.",
        ],
    }
