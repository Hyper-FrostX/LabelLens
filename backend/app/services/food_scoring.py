from typing import Any


FOOD_SCORE_VERSION = "label-lens-food-scores-v1"
NUTRITION_QUALITY_WEIGHTS = {
    "sugar": 40,
    "sodium": 30,
    "saturated_fat": 30,
}
NUTRITION_QUALITY_CAPS = {
    "sugar": 20,
    "sodium": 1000,
    "saturated_fat": 10,
}
PROTEIN_DENSITY_TARGET_G_PER_100_KCAL = 5.0
TRANSPARENCY_WEIGHTS = {
    "ingredients_list": 60,
    "allergen_declaration": 20,
    "may_contain_declaration": 20,
}


def _score_result(
    *,
    name: str,
    score: float | None,
    status: str,
    inputs: dict,
    formula: str,
    explanation: str,
    missing: list[str] | None = None,
) -> dict:
    return {
        "name": name,
        "score": round(score, 1) if score is not None else None,
        "status": status,
        "version": FOOD_SCORE_VERSION,
        "inputs": inputs,
        "formula": formula,
        "explanation": explanation,
        "missing_inputs": missing or [],
    }


def nutrition_quality_score(intelligence: dict) -> dict:
    values = intelligence["nutrient_density_per_100"]
    basis = intelligence.get("normalized_basis")
    required = ("sugar", "sodium", "saturated_fat")
    missing = [name for name in required if name not in values]
    if basis not in {"per_100g", "per_100ml"}:
        missing.append("compatible_per_100_basis")
    if missing:
        return _score_result(
            name="nutrition_quality",
            score=None,
            status="insufficient_data",
            inputs={name: values.get(name) for name in required},
            formula=(
                "100 - 40*min(sugars_g/20,1) - 30*min(sodium_mg/1000,1) "
                "- 30*min(saturated_fat_g/10,1)"
            ),
            explanation="A score requires the three named values on one compatible per-100 basis.",
            missing=missing,
        )
    if any(values[name]["basis"] != basis for name in required):
        return _score_result(
            name="nutrition_quality",
            score=None,
            status="insufficient_data",
            inputs={name: values[name] for name in required},
            formula="Versioned Label Lens project heuristic; see score inputs.",
            explanation="The nutrient values do not share one compatible basis.",
            missing=["compatible_per_100_basis"],
        )
    penalty = sum(
        NUTRITION_QUALITY_WEIGHTS[name]
        * min(values[name]["value"] / NUTRITION_QUALITY_CAPS[name], 1)
        for name in required
    )
    return _score_result(
        name="nutrition_quality",
        score=max(0, 100 - penalty),
        status="available",
        inputs={name: values[name] for name in required},
        formula=(
            "100 - 40*min(sugars_g/20,1) - 30*min(sodium_mg/1000,1) "
            "- 30*min(saturated_fat_g/10,1)"
        ),
        explanation=(
            "A project-defined per-100 heuristic that penalizes higher sugars, "
            "sodium, and saturated fat. It is not a regulatory grade or dietary recommendation."
        ),
    )


def protein_quality_score(intelligence: dict) -> dict:
    ratio = intelligence.get("ratios", {}).get("protein_g_per_100_kcal")
    if ratio is None:
        density = intelligence["nutrient_density_per_100"]
        missing = []
        if "protein" not in density:
            missing.append("protein_g")
        if "energy" not in density:
            missing.append("energy_kcal")
        return _score_result(
            name="protein_quality",
            score=None,
            status="insufficient_data",
            inputs={key: density.get(key) for key in ("protein", "energy")},
            formula=f"min(protein_g_per_100_kcal / {PROTEIN_DENSITY_TARGET_G_PER_100_KCAL}, 1) * 100",
            explanation="Protein density is not available on a shared per-100 basis.",
            missing=missing or ["positive_energy_value"],
        )
    return _score_result(
        name="protein_quality",
        score=min(ratio / PROTEIN_DENSITY_TARGET_G_PER_100_KCAL, 1) * 100,
        status="available",
        inputs={"protein_g_per_100_kcal": ratio},
        formula=f"min(protein_g_per_100_kcal / {PROTEIN_DENSITY_TARGET_G_PER_100_KCAL}, 1) * 100",
        explanation=(
            "This project index measures protein grams per 100 kcal only; "
            "it does not measure amino-acid profile, digestibility, or overall protein quality."
        ),
    )


def ingredient_transparency_score(data: Any) -> dict:
    ingredients_available = (
        bool(data.ingredients)
        or bool(data.ingredients_text and data.ingredients_text.strip())
    )
    if not ingredients_available:
        return _score_result(
            name="ingredient_transparency",
            score=None,
            status="insufficient_data",
            inputs={},
            formula="60 if ingredient list supplied + 20 if allergen declaration supplied + 20 if may-contain declaration supplied",
            explanation="No ingredient list was supplied; missing declarations are not treated as violations.",
            missing=["ingredients_list"],
        )
    factors = {
        name: {
            "provided": provided,
            "weight": weight,
        }
        for name, provided, weight in (
            (
                "ingredients_list",
                True,
                TRANSPARENCY_WEIGHTS["ingredients_list"],
            ),
            (
                "allergen_declaration",
                data.allergens is not None,
                TRANSPARENCY_WEIGHTS["allergen_declaration"],
            ),
            (
                "may_contain_declaration",
                data.may_contain is not None,
                TRANSPARENCY_WEIGHTS["may_contain_declaration"],
            ),
        )
    }
    score = sum(
        item["weight"] for item in factors.values() if item["provided"]
    )
    return _score_result(
        name="ingredient_transparency",
        score=score,
        status="available" if score == 100 else "partial_data",
        inputs=factors,
        formula="60 if ingredient list supplied + 20 if allergen declaration supplied + 20 if may-contain declaration supplied",
        explanation=(
            "Measures which label text fields were supplied, not ingredient safety, "
            "accuracy, legality, or catalog recognition. Missing fields are not violations."
        ),
    )


def build_food_scores(
    intelligence: dict,
    *,
    data: Any,
    personalized_suitability: dict,
) -> dict:
    suitability_score = personalized_suitability.get("profile_alignment_score")
    return {
        "version": FOOD_SCORE_VERSION,
        "scores": {
            "nutrition_quality": nutrition_quality_score(intelligence),
            "protein_quality": protein_quality_score(intelligence),
            "ingredient_transparency": ingredient_transparency_score(data),
            "personalized_suitability": _score_result(
                name="personalized_suitability",
                score=suitability_score,
                status=personalized_suitability.get("score_status", "not_evaluated"),
                inputs=personalized_suitability.get("assessments", []),
                formula=(
                    "100 * assessments without a potential conflict / evaluated "
                    "profile assessments; unknown factors are not scored"
                ),
                explanation=(
                    "This is profile-factor alignment in submitted data only, "
                    "not a safety, medical, or clinical suitability score."
                ),
                missing=personalized_suitability.get("missing_inputs", []),
            ),
        },
        "disclaimer": (
            "These project-defined scores are not official grades, medical advice, "
            "or a determination that a product is safe or suitable."
        ),
    }
