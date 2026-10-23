import re


INGREDIENT_KNOWLEDGE_BASE = (
    {
        "canonical_name": "Peanut",
        "aliases": ("peanut", "peanuts", "groundnut", "groundnuts"),
        "function": "Food ingredient; adds flavor, texture, and protein.",
        "concern_level": "Established hazard in a specific context",
        "concern_status": "evidence_based",
        "explanation": (
            "Peanut is a major food allergen and can cause serious reactions "
            "in people with peanut allergy. This concern is specific to "
            "allergic individuals; a label match alone does not establish "
            "exposure amount or individual risk."
        ),
        "evidence_context": (
            "This source describes food-allergy hazards; the concern applies "
            "to people with peanut allergy."
        ),
        "evidence_source": "U.S. FDA, Food Allergies",
        "source_url": (
            "https://www.fda.gov/food/food-labeling-nutrition/"
            "food-allergies"
        ),
    },
    {
        "canonical_name": "Ascorbic acid",
        "aliases": ("ascorbic acid", "vitamin c", "e300"),
        "function": "Antioxidant; may also be used as a nutrient.",
        "concern_level": "No specific concern identified in current knowledge base",
        "concern_status": "no_specific_concern",
        "explanation": (
            "The current knowledge base identifies this ingredient's usual "
            "food function but does not identify a specific concern. This "
            "does not assess the amount or a person's individual needs."
        ),
        "evidence_context": (
            "The cited regulation describes permitted food use; it is not "
            "evidence that this ingredient is universally safe or risk-free."
        ),
        "evidence_source": "U.S. Electronic Code of Federal Regulations, 21 CFR §182.3013",
        "source_url": (
            "https://www.ecfr.gov/current/title-21/chapter-I/"
            "subchapter-B/part-182/section-182.3013"
        ),
    },
    {
        "canonical_name": "Citric acid",
        "aliases": ("citric acid", "e330", "ins 330"),
        "function": "Acidity regulator and flavoring agent.",
        "concern_level": "No specific concern identified in current knowledge base",
        "concern_status": "no_specific_concern",
        "explanation": (
            "The current knowledge base identifies this ingredient's usual "
            "food function but does not identify a specific concern. This "
            "does not assess the amount or a person's individual needs."
        ),
        "evidence_context": (
            "The cited regulation describes permitted food use; it is not "
            "evidence that this ingredient is universally safe or risk-free."
        ),
        "evidence_source": "U.S. Electronic Code of Federal Regulations, 21 CFR §184.1033",
        "source_url": (
            "https://www.ecfr.gov/current/title-21/chapter-I/"
            "subchapter-B/part-184/section-184.1033"
        ),
    },
    {
        "canonical_name": "Potassium sorbate",
        "aliases": ("potassium sorbate", "e202"),
        "function": "Preservative used to inhibit yeast and mold growth.",
        "concern_level": "Insufficient evidence for a specific health concern",
        "concern_status": "insufficient_evidence",
        "explanation": (
            "The cited regulatory food-use source does not establish a "
            "specific health concern for this label. The label does not "
            "provide an amount or total exposure."
        ),
        "evidence_context": (
            "The cited source concerns regulatory food-use conditions, not "
            "evidence of a specific health risk. Regulatory permission is "
            "not itself proof of harm or absence of risk."
        ),
        "evidence_source": "U.S. Electronic Code of Federal Regulations, 21 CFR §182.3640",
        "source_url": (
            "https://www.ecfr.gov/current/title-21/chapter-I/"
            "subchapter-B/part-182/section-182.3640"
        ),
    },
    {
        "canonical_name": "Sodium benzoate",
        "aliases": ("sodium benzoate", "e211"),
        "function": "Preservative.",
        "concern_level": "Insufficient evidence for a specific health concern",
        "concern_status": "insufficient_evidence",
        "explanation": (
            "The cited regulatory food-use source does not establish a "
            "specific health concern for this label. The label does not "
            "provide an amount or total exposure."
        ),
        "evidence_context": (
            "The cited source concerns regulatory food-use conditions, not "
            "evidence of a specific health risk. Regulatory permission is "
            "not itself proof of harm or absence of risk."
        ),
        "evidence_source": "U.S. Electronic Code of Federal Regulations, 21 CFR §184.1733",
        "source_url": (
            "https://www.ecfr.gov/current/title-21/chapter-I/"
            "subchapter-B/part-184/section-184.1733"
        ),
    },
)

_NO_CONCERN_EXPLANATION = (
    "The current knowledge base identifies this ingredient but does not "
    "identify a specific concern. This is not proof that it is safe or "
    "risk-free; the label does not establish amount or total exposure."
)
_NO_CONCERN_CONTEXT = (
    "No specific concern is identified in this prototype knowledge base. "
    "This is not a safety determination."
)


def _food_entry(
    canonical_name: str,
    aliases: tuple[str, ...],
    function: str,
) -> dict:
    return {
        "canonical_name": canonical_name,
        "aliases": aliases,
        "function": function,
        "concern_level": "No specific concern identified in current knowledge base",
        "concern_status": "no_specific_concern",
        "explanation": _NO_CONCERN_EXPLANATION,
        "evidence_context": _NO_CONCERN_CONTEXT,
        "evidence_source": None,
        "source_url": None,
    }


INGREDIENT_KNOWLEDGE_BASE += (
    _food_entry(
        "Rice grits",
        ("rice grits", "rice grit"),
        "Cereal ingredient; provides grain solids and texture.",
    ),
    _food_entry(
        "Potato flakes",
        ("potato flakes", "dehydrated potato flakes"),
        "Dehydrated potato ingredient; contributes bulk and texture.",
    ),
    _food_entry(
        "Corn grits",
        ("corn grits", "maize grits"),
        "Cereal ingredient; provides grain solids and texture.",
    ),
    _food_entry(
        "Edible vegetable oil",
        (
            "edible vegetable oil",
            "edible vegetable oil corn soybean oil",
            "edible vegetable oil (corn/soybean oil)",
            "vegetable oil corn soybean oil",
            "corn oil",
            "soybean oil",
            "soya oil",
        ),
        "Cooking or frying oil; the specific oil depends on the label text.",
    ),
    _food_entry(
        "Iodized salt",
        ("iodized salt", "iodised salt", "salt iodized", "salt iodised"),
        "Seasoning; iodized salt also provides added iodine.",
    ),
    _food_entry(
        "Sugar",
        ("sugar", "sucrose", "cane sugar"),
        "Sweetener.",
    ),
    _food_entry(
        "Calcium carbonate",
        ("calcium carbonate", "ins 170(i)"),
        "Food additive; the specific technical function depends on its use.",
    ),
    _food_entry(
        "Silicon dioxide",
        ("silicon dioxide", "silica", "ins 551"),
        "Anti-caking agent.",
    ),
    _food_entry(
        "Chilli powder",
        ("chilli powder", "chili powder", "chilli pwd", "chili pwd"),
        "Spice used for flavor and heat.",
    ),
    _food_entry(
        "Black pepper powder",
        (
            "black pepper powder",
            "black pepper pwd",
            "ground black pepper",
            "black pepper",
        ),
        "Spice used for flavor and pungency.",
    ),
    _food_entry(
        "Garlic and onion powder",
        (
            "garlic and onion powder",
            "garlic & onion powder",
            "garlic onion powder",
            "garlic and onion powders",
        ),
        "Seasoning blend used for flavor.",
    ),
    _food_entry(
        "Acetic acid",
        ("acetic acid", "ins 260"),
        "Acidity regulator and flavoring agent.",
    ),
    _food_entry(
        "Malic acid",
        ("malic acid", "ins 296"),
        "Acidity regulator and flavoring agent.",
    ),
    _food_entry(
        "Natural and nature-identical flavouring substances",
        (
            "natural and nature-identical flavouring substances",
            "natural and nature identical flavouring substances",
            "natural and nature-identical flavoring substances",
            "natural and nature identical flavoring substances",
        ),
        "Flavoring substances; the individual flavoring compounds are not specified.",
    ),
    _food_entry(
        "Tamarind powder",
        ("tamarind powder", "tamarind pwd"),
        "Food ingredient used for tart flavor.",
    ),
    _food_entry(
        "Disodium guanylate",
        ("disodium guanylate", "ins 627"),
        "Flavor enhancer.",
    ),
    _food_entry(
        "Disodium inosinate",
        ("disodium inosinate", "ins 631"),
        "Flavor enhancer.",
    ),
    _food_entry(
        "Spice extract",
        ("spice extract", "spice extracts"),
        "Flavoring ingredient derived from spices; the specific source is not stated.",
    ),
    _food_entry(
        "Paprika extract",
        ("paprika extract", "ins 160c(i)"),
        "Coloring food extract.",
    ),
)

_CONCERN_STATUSES = {
    "evidence_based",
    "context_dependent",
    "no_specific_concern",
    "insufficient_evidence",
    "unknown",
}


def _validate_knowledge_base() -> None:
    for entry in INGREDIENT_KNOWLEDGE_BASE:
        status = entry.get("concern_status")
        if status not in _CONCERN_STATUSES:
            raise ValueError(
                f"Invalid concern status for {entry['canonical_name']}."
            )
        if status in {"evidence_based", "context_dependent"}:
            has_verified_source = (
                entry.get("evidence_source")
                and str(entry.get("source_url", "")).startswith("https://")
            )
            if not (
                has_verified_source
                and entry.get("explanation")
                and entry.get("evidence_context")
            ):
                raise ValueError(
                    "Evidence concerns require explanation, context, "
                    "source name, and HTTPS source URL."
                )


_validate_knowledge_base()


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


_ALIAS_INDEX = {
    _normalize(alias): entry
    for entry in INGREDIENT_KNOWLEDGE_BASE
    for alias in entry["aliases"]
}


def _split_nested_ingredient(ingredient: str) -> list[str]:
    """Expand explicit comma/semicolon-separated nested ingredient groups."""
    opening = ingredient.find("(")
    if opening < 0:
        return [ingredient.strip()]

    depth = 0
    closing = None
    for index in range(opening, len(ingredient)):
        if ingredient[index] == "(":
            depth += 1
        elif ingredient[index] == ")":
            depth -= 1
            if depth == 0:
                closing = index
                break
    if closing is None:
        return [ingredient.strip()]

    contents = ingredient[opening + 1 : closing]
    if (
        not re.search(r"[,;]", contents)
        and _normalize(contents) not in _ALIAS_INDEX
    ):
        return [ingredient.strip()]

    prefix = ingredient[:opening].strip()
    suffix = ingredient[closing + 1 :].strip()
    nested_parts = re.split(r"[,;]", contents)
    expanded = [prefix] if prefix else []
    for part in nested_parts:
        expanded.extend(_split_nested_ingredient(part.strip()))
    if suffix:
        expanded.extend(_split_nested_ingredient(suffix))
    return [part for part in expanded if part]


def _ingredient_result(ingredient: str) -> dict:
    normalized = _normalize(ingredient)
    entry = _ALIAS_INDEX.get(normalized)
    if entry is None:
        return {
            "ingredient": ingredient,
            "original_label_text": ingredient,
            "normalized_name": None,
            "matched_name": None,
            "recognition_status": "Unrecognized or uncertain",
            "concern_status": "unknown",
            "function": "Not identified in the current knowledge base.",
            "concern_level": "Unrecognized or uncertain",
            "explanation": (
                "Evidence about this item has not been established in the "
                "current knowledge base. It is not classified as harmful; "
                "verify the label text and ingredient."
            ),
            "evidence_source": None,
            "source_url": None,
            "evidence_context": (
                "Evidence has not been established in the current "
                "knowledge base."
            ),
            "needs_review": True,
            "match_type": None,
        }

    return {
        "ingredient": ingredient,
        "original_label_text": ingredient,
        "normalized_name": entry["canonical_name"],
        "matched_name": entry["canonical_name"],
        "recognition_status": "Recognized",
        "concern_status": entry["concern_status"],
        "function": entry["function"],
        "concern_level": entry["concern_level"],
        "explanation": entry["explanation"],
        "evidence_source": entry["evidence_source"],
        "source_url": entry["source_url"],
        "evidence_context": entry["evidence_context"],
        "needs_review": False,
        "match_type": "exact_name_or_verified_alias",
    }


def analyze_ingredients(
    ingredients: list[str] | None,
    *,
    ingredients_available: bool,
) -> dict:
    """Match only exact normalized names and verified aliases."""
    if not ingredients_available:
        return {
            "status": "Unavailable",
            "message": (
                "An ingredient list was not available or readable. No "
                "ingredient analysis was performed."
            ),
            "ingredients": [],
            "evidence_concerns": [],
            "evidence_concern_count": 0,
            "needs_review": True,
        }

    if not ingredients:
        return {
            "status": "Needs review",
            "message": (
                "The ingredient list could not be separated into readable "
                "items. Review the extracted ingredient text."
            ),
            "ingredients": [],
            "evidence_concerns": [],
            "evidence_concern_count": 0,
            "needs_review": True,
        }

    results = []
    for ingredient in ingredients:
        normalized = _normalize(ingredient)
        if normalized in _ALIAS_INDEX:
            results.append(_ingredient_result(ingredient))
            continue

        results.extend(
            _ingredient_result(part)
            for part in _split_nested_ingredient(ingredient)
        )

    evidence_concerns = [
        item
        for item in results
        if item["concern_status"] in {"evidence_based", "context_dependent"}
        and item["evidence_source"]
        and item["source_url"]
        and item["explanation"]
        and item["evidence_context"]
    ]

    return {
        "status": "Available",
        "message": (
            "Ingredient flags are informational and do not, by themselves, "
            "show that a product is unsafe."
        ),
        "ingredients": results,
        "evidence_concerns": evidence_concerns,
        "evidence_concern_count": len(evidence_concerns),
        "needs_review": any(item["needs_review"] for item in results),
    }
