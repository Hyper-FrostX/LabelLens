from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ExpertiseLevel

if TYPE_CHECKING:
    from app.models.scan import Scan


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    health_profile: Mapped["HealthProfile | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    health_condition_selections: Mapped[list["UserHealthCondition"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    allergen_selections: Mapped[list["UserAllergen"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    scans: Mapped[list["Scan"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_health_profiles_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    expertise_level: Mapped[ExpertiseLevel] = mapped_column(
        SAEnum(
            ExpertiseLevel,
            values_callable=lambda enum_type: [item.value for item in enum_type],
            native_enum=False,
            create_constraint=True,
            name="expertise_level_values",
        ),
        default=ExpertiseLevel.BEGINNER,
        nullable=False,
    )
    dietary_preferences: Mapped[list[str] | None] = mapped_column(JSON)
    ingredient_exclusions: Mapped[list[str] | None] = mapped_column(JSON)
    nutrition_goals: Mapped[list[str] | None] = mapped_column(JSON)
    calorie_goal_kcal: Mapped[float | None] = mapped_column(Float)
    protein_goal_g: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="health_profile")


class HealthCondition(Base):
    __tablename__ = "health_conditions"
    __table_args__ = (
        UniqueConstraint("name", name="uq_health_conditions_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    user_selections: Mapped[list["UserHealthCondition"]] = relationship(
        back_populates="condition",
        passive_deletes=True,
    )


class UserHealthCondition(Base):
    __tablename__ = "user_health_conditions"
    __table_args__ = (
        Index(
            "ix_user_health_conditions_condition_id",
            "condition_id",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    condition_id: Mapped[int] = mapped_column(
        ForeignKey("health_conditions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user: Mapped[User] = relationship(back_populates="health_condition_selections")
    condition: Mapped[HealthCondition] = relationship(back_populates="user_selections")


class Allergen(Base):
    __tablename__ = "allergens"
    __table_args__ = (
        UniqueConstraint("name", name="uq_allergens_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)

    user_selections: Mapped[list["UserAllergen"]] = relationship(
        back_populates="allergen",
        passive_deletes=True,
    )
    aliases: Mapped[list["AllergenAlias"]] = relationship(
        back_populates="allergen",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    ingredients: Mapped[list["IngredientAllergen"]] = relationship(
        back_populates="allergen",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserAllergen(Base):
    __tablename__ = "user_allergens"
    __table_args__ = (
        CheckConstraint(
            "allergen_id IS NOT NULL OR "
            "(custom_allergen_name IS NOT NULL AND "
            "length(trim(custom_allergen_name)) > 0)",
            name="has_catalog_or_custom_allergen",
        ),
        UniqueConstraint(
            "user_id",
            "allergen_id",
            name="uq_user_allergens_user_catalog",
        ),
        UniqueConstraint(
            "user_id",
            "custom_allergen_name",
            name="uq_user_allergens_user_custom",
        ),
        Index("ix_user_allergens_allergen_id", "allergen_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    allergen_id: Mapped[int | None] = mapped_column(
        ForeignKey("allergens.id", ondelete="CASCADE")
    )
    custom_allergen_name: Mapped[str | None] = mapped_column(String(120))

    user: Mapped[User] = relationship(back_populates="allergen_selections")
    allergen: Mapped[Allergen | None] = relationship(
        back_populates="user_selections"
    )
