import re

INGREDIENT_KNOWLEDGE_BASE = (
    {
        "canonical_name": "Peanut",
        "aliases": ("peanut", "peanuts", "groundnut", "groundnuts"),
        "function": "Food ingredient; adds flavor, texture, and protein.",
        "concern_level": "Established hazard in a specific context",
        "concern_status": "evidence_based",
        "evidence_verified": True,
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


_ADDITIVE_CODE_PATTERN = re.compile(
    r"(?<![a-z0-9])(?P<kind>ins|e)\s*[- ]?\s*"
    r"(?P<value>\d{3,4}[a-z]?(?:\([ivx]+\))?)(?![a-z0-9])",
    re.IGNORECASE,
)


def _normalized_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def contains_exact_phrase(text: str, phrase: str) -> bool:
    words = re.sub(r"[^a-z0-9]+", " ", phrase.casefold()).strip()
    if not words:
        return False
    pattern = r"(?<![a-z0-9])" + r"[\s_-]+".join(
        re.escape(word) for word in words.split()
    ) + r"(?![a-z0-9])"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        prefix = text[max(0, match.start() - 24) : match.start()]
        suffix = text[match.end() : match.end() + 12]
        if re.search(
            r"(?:\bno\b|\bwithout\b|\bfree\s+(?:of|from)\b|"
            r"\bnon[\s-]?)\s*$",
            prefix,
            re.IGNORECASE,
        ):
            continue
        if re.match(r"[\s-]*free\b", suffix, re.IGNORECASE):
            continue
        return True
    return False


def _catalog_records(database_records: list[dict] | None = None) -> list[dict]:
    from app.data.ingredient_knowledge import get_curated_ingredient_records

    curated = get_curated_ingredient_records()
    by_name = {
        record["canonical_name"].casefold(): record
        for record in curated
    }
    if database_records:
        for record in database_records:
            if record.get("__allergen_catalog__"):
                name = record["canonical_name"]
                existing = next(
                    (
                        item
                        for item in curated
                        if item.get("__allergen_catalog__")
                        and item["canonical_name"].casefold() == name.casefold()
                    ),
                    None,
                )
                if existing is None:
                    curated.append(record)
                else:
                    existing["aliases"] = list(
                        dict.fromkeys(
                            [*existing.get("aliases", []), *record.get("aliases", [])]
                        )
                    )
                continue
            key = record["canonical_name"].casefold()
            fallback = by_name.get(key)
            if fallback is None:
                curated.append(record)
                by_name[key] = record
                continue
            merged = dict(fallback)
            merged.update(record)
            for field in ("aliases", "categories", "functions", "identifiers"):
                merged[field] = list(
                    dict.fromkeys(
                        [*fallback.get(field, []), *record.get(field, [])]
                    )
                )
            for field in (
                "allergens",
                "evidence",
                "regulatory_references",
                "common_food_applications",
            ):
                if record.get(field):
                    merged[field] = record[field]
            merged["concern_status"] = fallback.get(
                "concern_status",
                "unknown",
            )
            merged["concern_level"] = fallback.get(
                "concern_level",
                "Unverified",
            )
            merged["explanation"] = fallback.get(
                "explanation",
                "No health conclusion is established in the current record.",
            )
            merged["evidence_context"] = fallback.get("evidence_context")
            by_name[key] = merged
            curated[curated.index(fallback)] = merged
    return curated


def _record_match_method(ingredient: str, record: dict) -> str | None:
    normalized = _normalize(ingredient)
    if normalized == _normalize(record["canonical_name"]):
        return "canonical_name"
    if any(normalized == _normalize(alias) for alias in record.get("aliases", [])):
        return "catalog_alias"

    identifiers = record.get("identifiers", [])
    for match in _ADDITIVE_CODE_PATTERN.finditer(ingredient):
        identifier_type = "INS" if match.group("kind").casefold() == "ins" else "E_NUMBER"
        value = _normalized_identifier(match.group("value"))
        if any(
            identifier_type == kind
            and value
            == _normalized_identifier(
                re.sub(r"^e", "", identifier_value, flags=re.IGNORECASE)
                if kind == "E_NUMBER"
                else identifier_value
            )
            for kind, identifier_value in identifiers
        ):
            return "additive_identifier"

    if re.fullmatch(r"\d{3,4}[a-z]?(?:\([ivx]+\))?", ingredient.strip(), re.I):
        value = _normalized_identifier(ingredient)
        if any(
            value == _normalized_identifier(identifier_value)
            for _, identifier_value in identifiers
        ):
            return "bare_additive_identifier"
    return None


def _record_result(ingredient: str, record: dict, method: str) -> dict:
    identifiers = [
        {"type": identifier_type, "value": value}
        for identifier_type, value in record.get("identifiers", [])
    ]
    evidence = record.get("evidence", [])
    verified_concerns = [
        item
        for item in evidence
        if item.get("verified")
        and item.get("classification") in {"established", "context_dependent"}
    ]
    if verified_concerns:
        concern_status = (
            "evidence_based"
            if record.get("concern_status") == "evidence_based"
            or any(
                item.get("classification") == "established"
                for item in verified_concerns
            )
            else "context_dependent"
        )
        concern_level = record.get(
            "concern_level",
            "Context-dependent evidence; product exposure is unknown",
        )
    elif record.get("verification_status") != "VERIFIED":
        concern_status = "unknown"
        concern_level = "Needs review"
    elif record.get("concern_status") in {
        "no_specific_concern",
        "insufficient_evidence",
        "unknown",
    }:
        concern_status = record["concern_status"]
        concern_level = record.get("concern_level", "Unverified")
    else:
        concern_status = "unknown"
        concern_level = "Unverified"

    explanations = [
        item.get("statement")
        for item in verified_concerns
        if item.get("statement")
    ]
    explanation = " ".join(explanations) if explanations else (
        "The current source review does not establish a health conclusion "
        "for this record. Identity, function, or use details may still need "
        "verification."
        if record.get("verification_status")
        in {"PROVISIONAL", "UNVERIFIED", "REVIEW_REQUIRED"}
        else record.get("explanation")
        or "The record identifies this item but does not establish a health concern."
    )
    sources = []
    for item in [*evidence, *record.get("regulatory_references", [])]:
        if not item.get("source_name") and not item.get("source_url"):
            continue
        source = {
            "source_name": item.get("source_name"),
            "source_url": item.get("source_url"),
            "verified": bool(item.get("verified")),
        }
        if source not in sources:
            sources.append(source)

    functions = record.get("functions") or (
        [record["function"]] if record.get("function") else []
    )
    return {
        "ingredient": ingredient,
        "original_label_text": ingredient,
        "canonical_name": record["canonical_name"],
        "normalized_name": record["canonical_name"],
        "matched_name": record["canonical_name"],
        "identifiers": identifiers,
        "category": record.get("categories", []),
        "functions": functions,
        "function": "; ".join(functions) or "Not specified in the knowledge base.",
        "description": record.get("description"),
        "common_food_applications": record.get("common_food_applications", []),
        "processing_purpose": record.get("purposes", []),
        "allergen_associations": record.get("allergens", []),
        "evidence": evidence,
        "source_references": sources,
        "evidence_quality": record.get("evidence_quality", "unreviewed"),
        "verification_status": record.get(
            "verification_status",
            "UNVERIFIED",
        ),
        "last_reviewed_at": record.get("last_reviewed_at"),
        "vegetarian_status": record.get("vegetarian_status"),
        "vegan_status": record.get("vegan_status"),
        "recognition_status": "Recognized",
        "concern_status": concern_status,
        "concern_level": concern_level,
        "explanation": explanation,
        "evidence_source": (
            verified_concerns[0].get("source_name")
            if verified_concerns
            else None
        ),
        "source_url": (
            verified_concerns[0].get("source_url")
            if verified_concerns
            else None
        ),
        "evidence_context": (
            record.get("evidence_context")
            if verified_concerns
            else (
                "Reference and health claims require source review; "
                "no safety conclusion is established."
            )
        ),
        "needs_review": record.get("evidence_quality") != "source_backed",
        "match_type": method,
        "match_quality": "exact",
        "confidence": "exact_catalog_match",
    }


def _unknown_record_result(ingredient: str) -> dict:
    return {
        "ingredient": ingredient,
        "original_label_text": ingredient,
        "canonical_name": None,
        "normalized_name": None,
        "matched_name": None,
        "identifiers": [],
        "category": [],
        "functions": [],
        "function": "Not identified in the current knowledge base.",
        "description": None,
        "common_food_applications": [],
        "processing_purpose": [],
        "allergen_associations": [],
        "evidence": [],
        "source_references": [],
        "evidence_quality": "unreviewed",
        "last_reviewed_at": None,
        "vegetarian_status": None,
        "vegan_status": None,
        "recognition_status": "Unrecognized or uncertain",
        "concern_status": "unknown",
        "concern_level": "Unrecognized or uncertain",
        "explanation": (
            "This text does not match the current ingredient knowledge base. "
            "It is not classified as harmful, and no identity or health "
            "property is inferred; review the label."
        ),
        "evidence_source": None,
        "source_url": None,
        "evidence_context": "No verified catalog match was found.",
        "needs_review": True,
        "match_type": None,
        "match_quality": "unmatched",
        "confidence": None,
    }


def match_allergen_text(
    allergen_name: str,
    text: str,
    *,
    knowledge_records: list[dict] | None = None,
) -> str | None:
    records = _catalog_records(knowledge_records)
    allergen_records = [
        record for record in records if record.get("__allergen_catalog__")
    ]
    normalized_target = _normalize(allergen_name)
    aliases = [allergen_name]
    for record in allergen_records:
        record_names = [
            record["canonical_name"],
            *record.get("aliases", []),
        ]
        if any(_normalize(name) == normalized_target for name in record_names):
            aliases = record_names
            break
    for alias in aliases:
        if contains_exact_phrase(text, alias):
            return alias
    return None


def analyze_ingredients(
    ingredients: list[str] | None,
    *,
    ingredients_available: bool,
    knowledge_records: list[dict] | None = None,
) -> dict:
    if not ingredients_available:
        return {
            "status": "Unavailable",
            "message": (
                "An ingredient list was not available or readable. No "
                "ingredient analysis was performed."
            ),
            "ingredients": [],
            "findings": [],
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
            "findings": [],
            "evidence_concerns": [],
            "evidence_concern_count": 0,
            "needs_review": True,
        }

    catalog = _catalog_records(knowledge_records)
    ingredient_catalog = [
        record for record in catalog if not record.get("__allergen_catalog__")
    ]
    results = []
    expanded_ingredients = []
    for ingredient in ingredients:
        if not isinstance(ingredient, str) or not ingredient.strip():
            continue
        expanded_ingredients.extend(_split_nested_ingredient(ingredient.strip()))

    for text in expanded_ingredients:
        method_record = next(
            (
                (record, method)
                for record in ingredient_catalog
                if (method := _record_match_method(text, record)) is not None
            ),
            None,
        )
        if method_record is not None:
            results.append(_record_result(text, *method_record))
            continue
        parts = _split_nested_ingredient(text)
        for part in parts:
            nested_match = next(
                (
                    (record, method)
                    for record in ingredient_catalog
                    if (method := _record_match_method(part, record)) is not None
                ),
                None,
            )
            results.append(
                _record_result(part, *nested_match)
                if nested_match
                else _unknown_record_result(part)
            )

    evidence_concerns = [
        result
        for result in results
        if result["concern_status"] in {"evidence_based", "context_dependent"}
        and result["evidence"]
        and any(
            item.get("verified")
            and item.get("classification") in {"established", "context_dependent"}
            and item.get("source_url", "").startswith("https://")
            for item in result["evidence"]
        )
    ]
    return {
        "status": "Available",
        "message": (
            "Ingredient matches and evidence are informational. A missing "
            "match does not establish that an ingredient is absent or that "
            "a product is safe."
        ),
        "ingredients": results,
        "findings": results,
        "evidence_concerns": evidence_concerns,
        "evidence_concern_count": len(evidence_concerns),
        "needs_review": any(item["needs_review"] for item in results),
    }
