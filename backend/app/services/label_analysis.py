from app.services.ingredient_analysis import analyze_ingredients
from app.services.label_parser import split_ingredients_text
from app.services.nutrition import (
    analyze_excess_nutrients,
    calculate_health_score,
)


def analyze_label(data, *, knowledge_records: list[dict] | None = None) -> dict:
    ingredients = getattr(data, "ingredients", None)
    ingredients_text = data.ingredients_text
    if ingredients is None and ingredients_text is not None:
        ingredients = split_ingredients_text(ingredients_text)

    units = {
        "total_sugar": data.sugar_unit,
        "added_sugar": data.added_sugar_unit,
        "sodium": data.sodium_unit,
        "saturated_fat": data.saturated_fat_unit,
    }
    return {
        "basis": data.basis,
        "excess_nutrients": analyze_excess_nutrients(
            sugar_g=data.sugar_g,
            added_sugar_g=data.added_sugar_g,
            sodium_mg=data.sodium_mg,
            saturated_fat_g=data.saturated_fat_g,
            basis=data.basis,
            units=units,
            serving_size_text=data.serving_size_text,
        ),
        "health_score": calculate_health_score(
            sugar_g=data.sugar_g,
            added_sugar_g=data.added_sugar_g,
            sodium_mg=data.sodium_mg,
            saturated_fat_g=data.saturated_fat_g,
            basis=data.basis,
            units=units,
            serving_size_text=data.serving_size_text,
        ),
        "ingredient_analysis": analyze_ingredients(
            ingredients,
            ingredients_available=(
                ingredients_text is not None or getattr(data, "ingredients", None) is not None
            ),
            knowledge_records=knowledge_records,
        ),
        "note": (
            "These project-defined nutrient references and curated "
            "ingredient notes are informational. They are not medical "
            "advice, official nutrition grades, or proof that a product "
            "is safe or unsafe."
        ),
    }
