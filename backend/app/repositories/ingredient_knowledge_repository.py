import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.data.ingredient_knowledge import CATEGORY_NAMES, get_curated_ingredient_records
from app.models import (
    AdditiveIdentifier,
    Allergen,
    AllergenAlias,
    Ingredient,
    IngredientAlias,
    IngredientAllergen,
    IngredientCategory,
    IngredientCategoryLink,
    IngredientEvidence,
    IngredientFunction,
    IngredientFunctionLink,
    IngredientRegulatoryReference,
)


def normalize_ingredient_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


class IngredientKnowledgeRepository:
    @staticmethod
    def load_catalog(session: Session) -> list[dict]:
        ingredients = session.scalars(
            select(Ingredient).options(
                selectinload(Ingredient.aliases),
                selectinload(Ingredient.identifiers),
                selectinload(Ingredient.categories).selectinload(
                    IngredientCategoryLink.category
                ),
                selectinload(Ingredient.functions).selectinload(
                    IngredientFunctionLink.function
                ),
                selectinload(Ingredient.allergen_associations).selectinload(
                    IngredientAllergen.allergen
                ).selectinload(Allergen.aliases),
                selectinload(Ingredient.evidence),
                selectinload(Ingredient.regulatory_references),
            )
        ).all()
        ingredient_records = [
            {
                "canonical_name": ingredient.canonical_name,
                "aliases": [alias.alias for alias in ingredient.aliases],
                "identifiers": [
                    (identifier.identifier_type, identifier.identifier_value)
                    for identifier in ingredient.identifiers
                ],
                "description": ingredient.description,
                "common_food_applications": ingredient.common_food_applications or [],
                "ingredient_type": ingredient.ingredient_type,
                "categories": [
                    link.category.name
                    for link in ingredient.categories
                ],
                "functions": [
                    link.function.name
                    for link in ingredient.functions
                ],
                "function": "; ".join(
                    link.function.name for link in ingredient.functions
                ),
                "purposes": [
                    link.technological_purpose
                    for link in ingredient.functions
                    if link.technological_purpose
                ],
                "allergens": [
                    {
                        "name": association.allergen.name,
                        "aliases": [
                            alias.alias for alias in association.allergen.aliases
                        ],
                        "association_type": association.association_type,
                        "source_reference": association.source_reference,
                        "verification_status": association.verification_status,
                    }
                    for association in ingredient.allergen_associations
                ],
                "evidence": [
                    {
                        "statement": evidence.statement,
                        "classification": evidence.evidence_classification,
                        "source_name": evidence.source_name,
                        "source_url": evidence.source_url,
                        "publication_date": (
                            evidence.publication_date.isoformat()
                            if evidence.publication_date
                            else None
                        ),
                        "limitations": evidence.limitations,
                        "verified": evidence.verified,
                        "reviewed_at": (
                            evidence.reviewed_at.isoformat()
                            if evidence.reviewed_at
                            else None
                        ),
                    }
                    for evidence in ingredient.evidence
                ],
                "regulatory_references": [
                    {
                        "jurisdiction": reference.jurisdiction,
                        "framework": reference.framework,
                        "status": reference.regulatory_status,
                        "usage_conditions": reference.usage_conditions,
                        "source_name": reference.source_name,
                        "source_url": reference.source_url,
                        "verified": reference.verified,
                        "reviewed_at": (
                            reference.reviewed_at.isoformat()
                            if reference.reviewed_at
                            else None
                        ),
                    }
                    for reference in ingredient.regulatory_references
                ],
                "evidence_quality": ingredient.evidence_quality,
                "verification_status": ingredient.verification_status,
                "last_reviewed_at": (
                    ingredient.last_reviewed_at.isoformat()
                    if ingredient.last_reviewed_at
                    else None
                ),
                "vegetarian_status": ingredient.vegetarian_status,
                "vegan_status": ingredient.vegan_status,
            }
            for ingredient in ingredients
        ]
        allergens = session.scalars(
            select(Allergen).options(selectinload(Allergen.aliases))
        ).all()
        return ingredient_records + [
            {
                "__allergen_catalog__": True,
                "canonical_name": allergen.name,
                "aliases": [alias.alias for alias in allergen.aliases],
                "alias_verification_statuses": [
                    alias.verification_status for alias in allergen.aliases
                ],
            }
            for allergen in allergens
        ]

    @staticmethod
    def seed_curated_data(session: Session) -> dict[str, int]:
        records = get_curated_ingredient_records()
        ingredient_records = [
            record for record in records if not record.get("__allergen_catalog__")
        ]
        allergen_records = [
            record for record in records if record.get("__allergen_catalog__")
        ]
        ingredients_by_name = {
            ingredient.canonical_name.casefold(): ingredient
            for ingredient in session.scalars(select(Ingredient)).all()
        }
        added_ingredients = 0
        added_aliases = 0
        added_identifiers = 0
        added_relations = 0
        added_evidence = 0
        added_regulatory = 0
        added_allergens = 0

        categories_by_name = {
            category.normalized_name: category
            for category in session.scalars(select(IngredientCategory)).all()
        }
        for name in CATEGORY_NAMES:
            normalized = normalize_ingredient_text(name)
            if normalized not in categories_by_name:
                category = IngredientCategory(name=name, normalized_name=normalized)
                session.add(category)
                session.flush()
                categories_by_name[normalized] = category

        functions_by_name = {
            function.normalized_name: function
            for function in session.scalars(select(IngredientFunction)).all()
        }
        alias_owners = {
            alias.normalized_alias: alias.ingredient_id
            for alias in session.scalars(select(IngredientAlias)).all()
        }
        identifiers_by_key = {
            (identifier.identifier_type, identifier.normalized_value)
            for identifier in session.scalars(select(AdditiveIdentifier)).all()
        }
        allergens_by_name = {
            allergen.name.casefold(): allergen
            for allergen in session.scalars(select(Allergen)).all()
        }

        # Reuse an existing allergen if its canonical name is one of its known
        # aliases instead of creating a second catalog record.
        allergen_alias_owner = {}
        for allergen in allergens_by_name.values():
            allergen_alias_owner[normalize_ingredient_text(allergen.name)] = allergen
        allergen_aliases_by_key = {
            alias.normalized_alias: alias.allergen
            for alias in session.scalars(
                select(AllergenAlias).options(selectinload(AllergenAlias.allergen))
            ).all()
        }
        for record in allergen_records:
            canonical = record["canonical_name"]
            matching = next(
                (
                    allergen_alias_owner[normalize_ingredient_text(alias)]
                    for alias in [canonical, *record["aliases"]]
                    if normalize_ingredient_text(alias) in allergen_alias_owner
                ),
                None,
            )
            allergen = matching or allergens_by_name.get(canonical.casefold())
            if allergen is None:
                allergen = Allergen(name=canonical, category="food")
                session.add(allergen)
                session.flush()
                allergens_by_name[canonical.casefold()] = allergen
                allergen_alias_owner[normalize_ingredient_text(canonical)] = allergen
                added_allergens += 1
            for alias_text in [canonical, *record["aliases"]]:
                normalized = normalize_ingredient_text(alias_text)
                existing = allergen_aliases_by_key.get(normalized)
                if existing is not None:
                    if existing.id != allergen.id:
                        # Some aliases legitimately belong to more than one
                        # allergen category (for example Wheat is associated
                        # with Gluten). Keep the existing alias owner and keep
                        # the canonical category available through its aliases.
                        continue
                    existing.verification_status = record.get(
                        "verification_status",
                        "REVIEW_REQUIRED",
                    )
                    continue
                session.add(
                    AllergenAlias(
                        allergen_id=allergen.id,
                        alias=alias_text,
                        normalized_alias=normalized,
                        verification_status=record.get(
                            "verification_status",
                            "REVIEW_REQUIRED",
                        ),
                    )
                )
                allergen_aliases_by_key[normalized] = allergen

        for record in ingredient_records:
            canonical = record["canonical_name"]
            ingredient = ingredients_by_name.get(canonical.casefold())
            if ingredient is None:
                ingredient = Ingredient(
                    canonical_name=canonical,
                    description=record.get("description"),
                    common_food_applications=record.get("common_food_applications"),
                    ingredient_type=record["ingredient_type"],
                    evidence_reference=None,
                    vegetarian_status=record.get("vegetarian_status"),
                    vegan_status=record.get("vegan_status"),
                    evidence_quality=record["evidence_quality"],
                    verification_status=record.get(
                        "verification_status",
                        "REVIEW_REQUIRED",
                    ),
                    last_reviewed_at=record.get("last_reviewed_at"),
                )
                session.add(ingredient)
                session.flush()
                ingredients_by_name[canonical.casefold()] = ingredient
                added_ingredients += 1
            else:
                ingredient.verification_status = record.get(
                    "verification_status",
                    "REVIEW_REQUIRED",
                )
                ingredient.evidence_quality = record.get(
                    "evidence_quality",
                    "unreviewed",
                )
                ingredient.last_reviewed_at = record.get("last_reviewed_at")
                if ingredient.description is None:
                    ingredient.description = record.get("description")
                if (
                    ingredient.common_food_applications is None
                    and record.get("common_food_applications")
                ):
                    ingredient.common_food_applications = record[
                        "common_food_applications"
                    ]

            for alias_text in dict.fromkeys([canonical, *record["aliases"]]):
                normalized = normalize_ingredient_text(alias_text)
                owner_id = alias_owners.get(normalized)
                if owner_id is not None:
                    if owner_id != ingredient.id:
                        raise ValueError(
                            f"Ingredient alias {alias_text!r} maps to multiple canonical entries."
                        )
                    continue
                session.add(
                    IngredientAlias(
                        ingredient_id=ingredient.id,
                        alias=alias_text,
                        normalized_alias=normalized,
                    )
                )
                alias_owners[normalized] = ingredient.id
                added_aliases += 1

            for identifier_type, identifier_value in record["identifiers"]:
                normalized = normalize_identifier(identifier_value)
                key = (identifier_type, normalized)
                if key in identifiers_by_key:
                    continue
                session.add(
                    AdditiveIdentifier(
                        ingredient_id=ingredient.id,
                        identifier_type=identifier_type,
                        identifier_value=identifier_value,
                        normalized_value=normalized,
                    )
                )
                identifiers_by_key.add(key)
                added_identifiers += 1

            category_links = {link.category.normalized_name for link in ingredient.categories}
            for category_name in record["categories"]:
                category = categories_by_name[normalize_ingredient_text(category_name)]
                if category.normalized_name not in category_links:
                    ingredient.categories.append(
                        IngredientCategoryLink(category=category)
                    )
                    category_links.add(category.normalized_name)

            function_links = {
                link.function.normalized_name
                for link in ingredient.functions
            }
            for function_name in record["functions"]:
                normalized = normalize_ingredient_text(function_name)
                function = functions_by_name.get(normalized)
                if function is None:
                    function = IngredientFunction(
                        name=function_name,
                        normalized_name=normalized,
                    )
                    session.add(function)
                    session.flush()
                    functions_by_name[normalized] = function
                if normalized not in function_links:
                    ingredient.functions.append(
                        IngredientFunctionLink(
                            function=function,
                            technological_purpose=record.get("purpose"),
                        )
                    )
                    function_links.add(normalized)

            for allergen_name, association_type in record["allergens"]:
                allergen = allergens_by_name.get(allergen_name.casefold())
                if allergen is None:
                    allergen = next(
                        (
                            value
                            for value in allergen_aliases_by_key.values()
                            if value.name.casefold() == allergen_name.casefold()
                        ),
                        None,
                    )
                if allergen is None:
                    continue
                key = (ingredient.id, allergen.id, association_type)
                if not session.scalar(
                    select(IngredientAllergen).where(
                        IngredientAllergen.ingredient_id == key[0],
                        IngredientAllergen.allergen_id == key[1],
                        IngredientAllergen.association_type == key[2],
                    )
                ):
                    session.add(
                        IngredientAllergen(
                            ingredient_id=ingredient.id,
                            allergen_id=allergen.id,
                            association_type=association_type,
                            source_reference=(
                                "https://www.fda.gov/food/food-labeling-nutrition/food-allergies"
                            ),
                            verification_status=record.get(
                                "verification_status",
                                "REVIEW_REQUIRED",
                            ),
                        )
                    )
                    added_relations += 1
                else:
                    association = session.scalar(
                        select(IngredientAllergen).where(
                            IngredientAllergen.ingredient_id == key[0],
                            IngredientAllergen.allergen_id == key[1],
                            IngredientAllergen.association_type == key[2],
                        )
                    )
                    association.verification_status = record.get(
                        "verification_status",
                        "REVIEW_REQUIRED",
                    )

            for evidence in record["evidence"]:
                existing_evidence = session.scalar(
                    select(IngredientEvidence).where(
                        IngredientEvidence.ingredient_id == ingredient.id,
                        IngredientEvidence.statement == evidence["statement"],
                        IngredientEvidence.source_url == evidence.get("source_url"),
                    )
                )
                if existing_evidence is None:
                    session.add(
                        IngredientEvidence(
                            ingredient_id=ingredient.id,
                            statement=evidence["statement"],
                            evidence_classification=evidence["classification"],
                            source_name=evidence.get("source_name"),
                            source_url=evidence.get("source_url"),
                            limitations=evidence.get("limitations"),
                            verified=evidence.get("verified", False),
                            reviewed_at=evidence.get("reviewed_at"),
                        )
                    )
                    added_evidence += 1
                else:
                    existing_evidence.evidence_classification = evidence[
                        "classification"
                    ]
                    existing_evidence.verified = evidence.get("verified", False)
                    existing_evidence.limitations = evidence.get("limitations")
                    existing_evidence.reviewed_at = evidence.get("reviewed_at")

            for reference in record["regulatory_references"]:
                existing_reference = session.scalar(
                    select(IngredientRegulatoryReference).where(
                        IngredientRegulatoryReference.ingredient_id == ingredient.id,
                        IngredientRegulatoryReference.framework == reference["framework"],
                        IngredientRegulatoryReference.source_url == reference.get("source_url"),
                    )
                )
                if existing_reference is None:
                    session.add(
                        IngredientRegulatoryReference(
                            ingredient_id=ingredient.id,
                            jurisdiction=reference["jurisdiction"],
                            framework=reference["framework"],
                            regulatory_status=reference.get("status"),
                            usage_conditions=reference.get("usage_conditions"),
                            source_name=reference.get("source_name"),
                            source_url=reference.get("source_url"),
                            verified=reference.get("verified", False),
                        )
                    )
                    added_regulatory += 1
                else:
                    existing_reference.regulatory_status = reference.get("status")
                    existing_reference.usage_conditions = reference.get(
                        "usage_conditions"
                    )
                    existing_reference.reviewed_at = reference.get("reviewed_at")
                    existing_reference.verified = reference.get("verified", False)

        session.commit()
        return {
            "ingredients": added_ingredients,
            "aliases": added_aliases,
            "identifiers": added_identifiers,
            "allergen_associations": added_relations,
            "evidence": added_evidence,
            "regulatory_references": added_regulatory,
            "allergens": added_allergens,
        }
