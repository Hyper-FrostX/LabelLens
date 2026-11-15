from copy import deepcopy
from datetime import date
import re

from app.services.ingredient_allergen_aliases import ALLERGEN_ALIASES
from app.services.ingredient_analysis import INGREDIENT_KNOWLEDGE_BASE


_CODEX_GSFA_URL = "https://www.fao.org/gsfaonline/additives/index.html?lang=en"
_REVIEW_DATE = date(2026, 11, 15)
_INITIAL_ADDITIVES = (
    {
        "canonical_name": "Sodium benzoate",
        "aliases": ("benzoate of soda",),
        "ins": "211",
        "e_number": "E211",
        "category": "Preservatives",
        "functions": ("Preservative",),
        "purpose": "Used as a food preservative.",
    },
    {
        "canonical_name": "Potassium sorbate",
        "aliases": ("sorbate",),
        "ins": "202",
        "e_number": "E202",
        "category": "Preservatives",
        "functions": ("Preservative",),
        "purpose": "Used as a food preservative.",
    },
    {
        "canonical_name": "Citric acid",
        "aliases": (),
        "ins": "330",
        "e_number": "E330",
        "category": "Acidity regulators",
        "functions": ("Acidity regulator", "Flavoring agent"),
        "purpose": "Used as an acidity regulator and flavoring agent.",
    },
    {
        "canonical_name": "Monosodium glutamate",
        "aliases": ("MSG", "sodium glutamate"),
        "ins": "621",
        "e_number": "E621",
        "category": "Flavour enhancers",
        "functions": ("Flavour enhancer",),
        "purpose": "Used as a flavour enhancer.",
    },
    {
        "canonical_name": "Aspartame",
        "aliases": ("aspartame sweetener",),
        "ins": "951",
        "e_number": "E951",
        "category": "Sweeteners",
        "functions": ("Sweetener",),
        "purpose": "Used as a sweetener.",
    },
    {
        "canonical_name": "Sucralose",
        "aliases": (),
        "ins": "955",
        "e_number": "E955",
        "category": "Sweeteners",
        "functions": ("Sweetener",),
        "purpose": "Used as a sweetener.",
    },
)

CATEGORY_NAMES = (
    "Preservatives",
    "Artificial and natural colours",
    "Sweeteners",
    "Emulsifiers",
    "Stabilizers",
    "Thickeners",
    "Acidity regulators",
    "Antioxidants",
    "Flavour enhancers",
    "Raising agents",
    "Anti-caking agents",
    "Humectants",
    "Gelling agents",
    "Starches",
    "Oils and fats",
    "Sugars and sweeteners",
    "Proteins",
    "Other food ingredients",
)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _legacy_record(entry: dict) -> dict:
    record = {
        "canonical_name": entry["canonical_name"],
        "aliases": list(entry["aliases"]),
        "description": entry.get("explanation"),
        "function": entry["function"],
        "common_food_applications": [],
        "ingredient_type": (
            "food_additive"
            if any(re.search(r"\b(?:e|ins)\s*[- ]?\d", alias, re.I) for alias in entry["aliases"])
            else "food_ingredient"
        ),
        "categories": ["Other food ingredients"],
        "functions": [entry["function"]],
        "identifiers": [],
        "allergens": [],
        "evidence": [],
        "regulatory_references": [],
        "evidence_quality": "unreviewed",
        "verification_status": (
            "PROVISIONAL"
            if entry["canonical_name"].casefold() == "peanut"
            else "REVIEW_REQUIRED"
            if entry.get("source_url")
            else "UNVERIFIED"
        ),
        "last_reviewed_at": _REVIEW_DATE,
        "concern_status": entry.get("concern_status", "unknown"),
        "concern_level": entry.get("concern_level", "Unverified"),
        "explanation": entry.get("explanation"),
        "evidence_context": entry.get("evidence_context"),
        "evidence_source": entry.get("evidence_source"),
        "source_url": entry.get("source_url"),
        "vegetarian_status": None,
        "vegan_status": None,
    }

    for alias in entry["aliases"]:
        match = re.fullmatch(r"\s*ins\s*[- ]?\s*([0-9]+[a-z]?)\s*", alias, re.I)
        if match:
            record["identifiers"].append(("INS", match.group(1).upper()))
        match = re.fullmatch(r"\s*e\s*[- ]?\s*([0-9]+[a-z]?)\s*", alias, re.I)
        if match:
            record["identifiers"].append(("E_NUMBER", f"E{match.group(1).upper()}"))

    legacy_evidence_url = entry.get("source_url")
    legacy_evidence_source = entry.get("evidence_source")
    legacy_status = entry.get("concern_status")
    if (
        legacy_status == "evidence_based"
        and entry.get("evidence_verified") is True
        and legacy_evidence_url
    ):
        record["evidence"].append(
            {
                "statement": entry["explanation"],
                "classification": "context_dependent",
                "source_name": legacy_evidence_source,
                "source_url": legacy_evidence_url,
                "limitations": entry.get("evidence_context"),
                "verified": True,
                "reviewed_at": _REVIEW_DATE,
            }
        )
        record["evidence_quality"] = "source_backed"
    elif legacy_evidence_url and legacy_status in {
        "no_specific_concern",
        "insufficient_evidence",
    }:
        record["evidence"].append(
            {
                "statement": (
                    "The legacy knowledge base does not establish a specific "
                    "health concern. This regulatory reference alone does not "
                    "establish harm or safety."
                ),
                "classification": "uncertain",
                "source_name": legacy_evidence_source,
                "source_url": legacy_evidence_url,
                "limitations": "Regulatory food-use text is not a toxicological assessment.",
                "verified": False,
                "reviewed_at": _REVIEW_DATE,
            }
        )
        record["regulatory_references"].append(
            {
                "jurisdiction": "United States",
                "framework": legacy_evidence_source or "Legacy project reference",
                "source_name": legacy_evidence_source,
                "source_url": legacy_evidence_url,
                "verified": False,
                "reviewed_at": _REVIEW_DATE,
            }
        )

    if entry["canonical_name"].casefold() == "peanut":
        record["allergens"].append(("Peanuts", "direct"))
    return record


def get_curated_ingredient_records() -> list[dict]:
    records_by_name = {
        entry["canonical_name"].casefold(): _legacy_record(deepcopy(entry))
        for entry in INGREDIENT_KNOWLEDGE_BASE
    }
    for additive in _INITIAL_ADDITIVES:
        key = additive["canonical_name"].casefold()
        record = records_by_name.get(key)
        if record is None:
            record = {
                "canonical_name": additive["canonical_name"],
                "aliases": [],
                "description": None,
                "common_food_applications": [],
                "ingredient_type": "food_additive",
                "categories": [],
                "functions": [],
                "identifiers": [],
                "allergens": [],
                "evidence": [],
                "regulatory_references": [],
                "evidence_quality": "unverified",
                "verification_status": "REVIEW_REQUIRED",
                "last_reviewed_at": _REVIEW_DATE,
                "vegetarian_status": None,
                "vegan_status": None,
            }
            records_by_name[key] = record

        record["aliases"] = list(dict.fromkeys(
            [*record["aliases"], *additive["aliases"]]
        ))
        record["ingredient_type"] = "food_additive"
        record["categories"] = list(
            dict.fromkeys([*record["categories"], additive["category"]])
        )
        record["functions"] = list(
            dict.fromkeys([*record["functions"], *additive["functions"]])
        )
        record["identifiers"] = list(
            dict.fromkeys(
                [
                    *record["identifiers"],
                    ("INS", additive["ins"]),
                    ("E_NUMBER", additive["e_number"]),
                ]
            )
        )
        record["purpose"] = additive["purpose"]
        record["evidence_quality"] = "unverified"
        record["regulatory_references"].append(
            {
                "jurisdiction": "International",
                "framework": "Codex GSFA online database",
                "source_name": "Codex General Standard for Food Additives",
                "source_url": _CODEX_GSFA_URL,
                "verified": False,
                "reviewed_at": _REVIEW_DATE,
            }
        )
        if additive["canonical_name"] == "Aspartame":
            record["verification_status"] = "PROVISIONAL"
            record["evidence"].append(
                {
                    "statement": (
                        "IARC classified aspartame as possibly carcinogenic "
                        "to humans (Group 2B), citing limited evidence; "
                        "JECFA reaffirmed an acceptable daily intake of "
                        "40 mg/kg body weight. This hazard classification "
                        "does not determine risk from this product."
                    ),
                    "classification": "context_dependent",
                    "source_name": (
                        "IARC, Aspartame hazard and risk assessment results released"
                    ),
                    "source_url": (
                        "https://www.iarc.who.int/news-events/"
                        "aspartame-hazard-and-risk-assessment-results-released/"
                    ),
                    "publication_date": date(2023, 7, 14),
                    "limitations": (
                        "The IARC hazard classification and JECFA risk "
                        "assessment are distinct; product concentration and "
                        "consumption are unknown."
                    ),
                    "verified": True,
                    "reviewed_at": _REVIEW_DATE,
                }
            )

    allergens = []
    for canonical_name, aliases in ALLERGEN_ALIASES.items():
        allergens.append(
            {
                "canonical_name": canonical_name,
                "aliases": list(aliases),
                "verification_status": "REVIEW_REQUIRED",
            }
        )

    return [
        {
            **record,
            "aliases": list(dict.fromkeys(record["aliases"])),
            "identifiers": list(dict.fromkeys(record["identifiers"])),
        }
        for record in records_by_name.values()
    ] + [
        {
            "__allergen_catalog__": True,
            "canonical_name": item["canonical_name"],
            "aliases": item["aliases"],
            "verification_status": item["verification_status"],
        }
        for item in allergens
    ]
