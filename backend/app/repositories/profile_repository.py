from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Allergen,
    HealthCondition,
    HealthProfile,
    User,
    UserAllergen,
    UserHealthCondition,
)
from app.models.enums import ExpertiseLevel


class ProfileRepository:
    @staticmethod
    def get_for_user(session: Session, user_id: int) -> User | None:
        return session.scalar(
            select(User)
            .options(
                selectinload(User.health_profile),
                selectinload(User.health_condition_selections).selectinload(
                    UserHealthCondition.condition
                ),
                selectinload(User.allergen_selections).selectinload(
                    UserAllergen.allergen
                ),
            )
            .where(User.id == user_id)
        )

    @staticmethod
    def get_conditions(
        session: Session,
        names: Sequence[str],
    ) -> list[HealthCondition]:
        if not names:
            return []
        return list(
            session.scalars(
                select(HealthCondition).where(
                    func.lower(HealthCondition.name).in_(
                        [name.casefold() for name in names]
                    )
                )
            ).all()
        )

    @staticmethod
    def add_conditions(
        session: Session,
        conditions: Sequence[HealthCondition],
    ) -> None:
        session.add_all(conditions)
        session.flush()

    @staticmethod
    def get_allergens(
        session: Session,
        names: Sequence[str],
    ) -> list[Allergen]:
        if not names:
            return []
        return list(
            session.scalars(
                select(Allergen).where(
                    func.lower(Allergen.name).in_(
                        [name.casefold() for name in names]
                    )
                )
            ).all()
        )

    @staticmethod
    def add_allergens(session: Session, allergens: Sequence[Allergen]) -> None:
        session.add_all(allergens)
        session.flush()

    @staticmethod
    def save_selections(
        user: User,
        *,
        expertise_level: ExpertiseLevel,
        conditions: Sequence[HealthCondition],
        allergens: Sequence[Allergen],
        custom_allergens: Sequence[str],
        dietary_preferences: Sequence[str] = (),
        ingredient_exclusions: Sequence[str] = (),
        nutrition_goals: Sequence[str] = (),
        calorie_goal_kcal: float | None = None,
        protein_goal_g: float | None = None,
    ) -> None:
        if user.health_profile is None:
            user.health_profile = HealthProfile(expertise_level=expertise_level)
        else:
            user.health_profile.expertise_level = expertise_level
        user.health_profile.dietary_preferences = list(dietary_preferences)
        user.health_profile.ingredient_exclusions = list(ingredient_exclusions)
        user.health_profile.nutrition_goals = list(nutrition_goals)
        user.health_profile.calorie_goal_kcal = calorie_goal_kcal
        user.health_profile.protein_goal_g = protein_goal_g

        user.health_condition_selections = [
            UserHealthCondition(condition=condition) for condition in conditions
        ]
        user.allergen_selections = [
            UserAllergen(allergen=allergen) for allergen in allergens
        ] + [
            UserAllergen(custom_allergen_name=name) for name in custom_allergens
        ]
