from collections.abc import Sequence
from datetime import timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Allergen, HealthCondition, HealthProfile, User
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import (
    AllergenChoice,
    HealthConditionChoice,
    HealthProfileResponse,
    HealthProfileUpdate,
)

_ALLERGEN_CATEGORIES = {
    choice.value.casefold(): "food" for choice in AllergenChoice
}


class ProfilePersistenceConflict(Exception):
    """Raised when a profile update conflicts with persisted profile data."""


def _condition_map(
    conditions: Sequence[HealthCondition],
) -> dict[str, HealthCondition]:
    return {condition.name.casefold(): condition for condition in conditions}


def _allergen_map(allergens: Sequence[Allergen]) -> dict[str, Allergen]:
    return {allergen.name.casefold(): allergen for allergen in allergens}


def _build_response(user: User) -> HealthProfileResponse:
    profile = user.health_profile
    if profile is None:
        raise RuntimeError("Health profile was not initialized.")

    supported_conditions = {
        choice.value.casefold(): choice for choice in HealthConditionChoice
    }
    condition_names = []
    seen_conditions = set()
    for selection in user.health_condition_selections:
        condition = selection.condition
        choice = (
            supported_conditions.get(condition.name.casefold())
            if condition is not None
            else None
        )
        if choice is not None and choice not in seen_conditions:
            condition_names.append(choice)
            seen_conditions.add(choice)

    supported_allergens = {
        choice.value.casefold(): choice for choice in AllergenChoice
    }
    allergen_names = []
    custom_allergens = []
    seen_allergens = set()
    seen_custom = set()
    for selection in user.allergen_selections:
        if selection.allergen is not None:
            choice = supported_allergens.get(selection.allergen.name.casefold())
            if choice is not None and choice not in seen_allergens:
                allergen_names.append(choice)
                seen_allergens.add(choice)
        elif selection.custom_allergen_name:
            name = selection.custom_allergen_name.strip()
            key = name.casefold()
            if name and key not in seen_custom:
                custom_allergens.append(name)
                seen_custom.add(key)

    updated_at = profile.updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    return HealthProfileResponse(
        name=user.name,
        expertise_level=profile.expertise_level,
        health_conditions=condition_names,
        allergens=allergen_names,
        custom_allergens=custom_allergens,
        dietary_preferences=profile.dietary_preferences or [],
        ingredient_exclusions=profile.ingredient_exclusions or [],
        nutrition_goals=profile.nutrition_goals or [],
        calorie_goal_kcal=profile.calorie_goal_kcal,
        protein_goal_g=profile.protein_goal_g,
        updated_at=updated_at,
    )


def _ensure_health_profile(session: Session, user: User) -> User:
    if user.health_profile is not None:
        return user
    user.health_profile = HealthProfile()
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    except SQLAlchemyError:
        session.rollback()
        raise
    refreshed_user = ProfileRepository.get_for_user(session, user.id)
    if refreshed_user is None:
        raise RuntimeError("Authenticated user no longer exists.")
    return refreshed_user


def get_profile(session: Session, user_id: int) -> HealthProfileResponse | None:
    user = ProfileRepository.get_for_user(session, user_id)
    if user is None:
        return None
    user = _ensure_health_profile(session, user)
    return _build_response(user)


def update_profile(
    session: Session,
    user_id: int,
    data: HealthProfileUpdate,
) -> HealthProfileResponse | None:
    user = ProfileRepository.get_for_user(session, user_id)
    if user is None:
        return None
    try:
        condition_names = [condition.value for condition in data.health_conditions]
        existing_conditions = ProfileRepository.get_conditions(
            session,
            condition_names,
        )
        conditions_by_name = _condition_map(existing_conditions)
        new_conditions = [
            HealthCondition(name=name)
            for name in condition_names
            if name.casefold() not in conditions_by_name
        ]
        ProfileRepository.add_conditions(session, new_conditions)
        conditions_by_name.update(_condition_map(new_conditions))

        allergen_names = [allergen.value for allergen in data.allergens]
        existing_allergens = ProfileRepository.get_allergens(session, allergen_names)
        allergens_by_name = _allergen_map(existing_allergens)
        new_allergens = [
            Allergen(name=name, category=_ALLERGEN_CATEGORIES[name.casefold()])
            for name in allergen_names
            if name.casefold() not in allergens_by_name
        ]
        ProfileRepository.add_allergens(session, new_allergens)
        allergens_by_name.update(_allergen_map(new_allergens))

        user.name = data.name
        ProfileRepository.save_selections(
            user,
            expertise_level=data.expertise_level,
            conditions=[
                conditions_by_name[name.casefold()] for name in condition_names
            ],
            allergens=[
                allergens_by_name[name.casefold()] for name in allergen_names
            ],
            custom_allergens=data.custom_allergens,
            dietary_preferences=[item.value for item in data.dietary_preferences],
            ingredient_exclusions=data.ingredient_exclusions,
            nutrition_goals=[item.value for item in data.nutrition_goals],
            calorie_goal_kcal=data.calorie_goal_kcal,
            protein_goal_g=data.protein_goal_g,
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ProfilePersistenceConflict from error
    except SQLAlchemyError:
        session.rollback()
        raise

    updated_user = ProfileRepository.get_for_user(session, user_id)
    if updated_user is None:
        raise RuntimeError("Authenticated user no longer exists.")
    return _build_response(updated_user)
