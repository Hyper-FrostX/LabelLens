import math
import re
from typing import Any


NUTRITION_INTELLIGENCE_VERSION = "label-lens-nutrition-intelligence-v1"

_FIELDS = {
    "energy_kcal": ("kcal", "energy"),
    "energy_kj": ("kj", "energy_kj"),
    "total_fat_g": ("g", "total_fat"),
    "saturated_fat_g": ("g", "saturated_fat"),
    "trans_fat_g": ("g", "trans_fat"),
    "carbohydrates_g": ("g", "carbohydrates"),
    "sugar_g": ("g", "sugar"),
    "added_sugar_g": ("g", "added_sugar"),
    "protein_g": ("g", "protein"),
    "fiber_g": ("g", "fiber"),
    "sodium_mg": ("mg", "sodium"),
}
_CANONICAL_FIELDS = (
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
_SERVING_PATTERN = re.compile(
    r"(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|ml|l|grams?|milliliters?|millilitres?|liters?|litres?)\b",
    re.IGNORECASE,
)


def _convert_unit(value: float, unit: str | None, expected: str) -> float | None:
    if not math.isfinite(value) or value < 0 or not unit:
        return None
    normalized = unit.casefold().replace(" ", "")
    conversions = {
        ("mg", "g"): 0.001,
        ("g", "mg"): 1000.0,
        ("kj", "kcal"): 1 / 4.184,
    }
    if normalized == expected:
        return value
    factor = conversions.get((normalized, expected))
    return value * factor if factor is not None else None


def _source_values(data: Any) -> dict[str, tuple[float, str | None]]:
    values: dict[str, tuple[float, str | None]] = {}
    primary = {
        "sugar_g": (data.sugar_g, data.sugar_unit),
        "added_sugar_g": (data.added_sugar_g, data.added_sugar_unit),
        "sodium_mg": (data.sodium_mg, data.sodium_unit),
        "saturated_fat_g": (data.saturated_fat_g, data.saturated_fat_unit),
    }
    for name, (value, unit) in primary.items():
        if value is not None:
            values[name] = (value, unit)

    for name, item in data.additional_nutrients.items():
        value = item.value
        if value is not None and name in _FIELDS:
            # Explicit primary fields take precedence over duplicate extras.
            values.setdefault(name, (value, item.unit))
    return values


def _serving_amount(text: str | None) -> tuple[float, str] | None:
    if not text:
        return None
    match = _SERVING_PATTERN.search(text)
    if match is None:
        return None
    try:
        amount = float(match.group("amount").replace(",", "."))
    except ValueError:
        return None
    if not math.isfinite(amount) or amount <= 0:
        return None
    unit = match.group("unit").casefold()
    if unit in {"kg"}:
        return amount * 1000, "per_100g"
    if unit in {"g", "gram", "grams"}:
        return amount, "per_100g"
    if unit in {"l", "liter", "liters", "litre", "litres"}:
        return amount * 1000, "per_100ml"
    return amount, "per_100ml"


def build_nutrition_intelligence(data: Any, *, excess_nutrients: list | None = None) -> dict:
    source_values = _source_values(data)
    normalized_basis = data.basis if data.basis in {"per_100g", "per_100ml"} else None
    serving = _serving_amount(data.serving_size_text)
    if data.basis == "per_serving" and serving is not None:
        normalized_basis = serving[1]

    density: dict[str, dict] = {}
    per_serving: dict[str, dict] = {}
    for name, (raw_value, raw_unit) in source_values.items():
        if name == "energy_kj":
            continue
        expected, canonical = _FIELDS[name]
        value = _convert_unit(raw_value, raw_unit, expected)
        if value is None:
            continue
        per_serving_value = None
        if data.basis == "per_serving":
            per_serving_value = value
        elif (
            data.basis in {"per_100g", "per_100ml"}
            and serving is not None
            and serving[1] == data.basis
        ):
            per_serving_value = value * serving[0] / 100
        if per_serving_value is not None:
            per_serving[canonical] = {
                "value": round(per_serving_value, 4),
                "unit": expected,
                "source": "label_value_or_calculated_from_serving_size",
            }
        if normalized_basis and data.basis in {"per_100g", "per_100ml"}:
            density[canonical] = {
                "value": round(value, 4),
                "unit": expected,
                "basis": data.basis,
                "source_basis": data.basis,
                "normalization": "reported_per_100",
            }
        elif data.basis == "per_serving" and serving is not None:
            density[canonical] = {
                "value": round(value * 100 / serving[0], 4),
                "unit": expected,
                "basis": normalized_basis,
                "source_basis": "per_serving",
                "normalization": "calculated_from_metric_serving_size",
            }

    if "energy" not in density and "energy_kj" in source_values:
        raw_value, raw_unit = source_values["energy_kj"]
        kcal = _convert_unit(raw_value, raw_unit, "kcal")
        if kcal is not None:
            if data.basis in {"per_100g", "per_100ml"}:
                density["energy"] = {
                    "value": round(kcal, 4),
                    "unit": "kcal",
                    "basis": data.basis,
                    "source_basis": data.basis,
                    "normalization": "converted_from_kj",
                }
            elif data.basis == "per_serving" and serving is not None:
                density["energy"] = {
                    "value": round(kcal * 100 / serving[0], 4),
                    "unit": "kcal",
                    "basis": normalized_basis,
                    "source_basis": "per_serving",
                    "normalization": "converted_from_kj_and_metric_serving_size",
                }
            per_serving.setdefault(
                "energy",
                {"value": round(kcal, 4), "unit": "kcal", "source": "label_value"},
            )

    ratios = {}
    energy = density.get("energy")
    protein = density.get("protein")
    sugar = density.get("sugar")
    if energy and energy["value"] > 0 and protein and protein["basis"] == energy["basis"]:
        ratios["protein_g_per_100_kcal"] = round(
            protein["value"] * 100 / energy["value"],
            3,
        )
    if energy and energy["value"] > 0 and sugar and sugar["basis"] == energy["basis"]:
        ratios["sugar_energy_percent"] = round(
            sugar["value"] * 4 * 100 / energy["value"],
            2,
        )

    observations = []
    for nutrient, value, comparison, message in (
        (
            "added_sugar",
            per_serving.get("added_sugar"),
            per_serving.get("sugar"),
            "Reported added sugar is greater than reported total sugar; check the label values and units.",
        ),
        (
            "saturated_fat",
            per_serving.get("saturated_fat"),
            per_serving.get("total_fat"),
            "Reported saturated fat is greater than reported total fat; check the label values and units.",
        ),
    ):
        if value is not None and comparison is not None and value["value"] > comparison["value"]:
            observations.append(
                {
                    "type": "LABEL_VALUE_INCONSISTENCY",
                    "nutrient": nutrient,
                    "message": message,
                    "values": {"reported": value, "comparison": comparison},
                }
            )
    if excess_nutrients:
        observations.extend(
            {
                "type": "EXISTING_PROJECT_REFERENCE_ASSESSMENT",
                **item,
            }
            for item in excess_nutrients
        )

    return {
        "version": NUTRITION_INTELLIGENCE_VERSION,
        "status": (
            "available"
            if density or per_serving
            else "insufficient_data"
        ),
        "reported_basis": data.basis,
        "normalized_basis": normalized_basis,
        "nutrient_density_per_100": density,
        "per_serving": per_serving,
        "ratios": ratios,
        "ratio_methods": {
            "protein_g_per_100_kcal": (
                "protein_g_per_100 * 100 / energy_kcal_per_100"
            ),
            "sugar_energy_percent": (
                "sugar_g_per_100 * 4 kcal/g * 100 / energy_kcal_per_100; "
                "4 kcal/g is an approximate calculation factor"
            ),
        },
        "observations": observations,
        "missing_or_unusable_fields": sorted(
            set(_CANONICAL_FIELDS)
            - set(density)
            - set(per_serving)
        ),
        "limitations": [
            "Unit or basis conversions are performed only for recognized units and a stated metric serving size.",
            "Mass and volume bases (per 100 g and per 100 ml) are not treated as interchangeable.",
            "Derived densities do not establish nutrient quality, recommended intake, or medical suitability.",
        ],
    }
