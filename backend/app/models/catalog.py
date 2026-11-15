from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import NutrientBasis
from app.models.user import utc_now


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("barcode", name="uq_products_barcode"),
        Index("ix_products_product_name", "product_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_name: Mapped[str] = mapped_column(String(240), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(160))
    barcode: Mapped[str | None] = mapped_column(String(32))
    category: Mapped[str | None] = mapped_column(String(120))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    ingredients: Mapped[list["ProductIngredient"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductIngredient.ingredient_order",
        passive_deletes=True,
    )
    nutrients: Mapped[list["ProductNutrient"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (
        UniqueConstraint("canonical_name", name="uq_ingredients_canonical_name"),
        Index("ix_ingredients_ingredient_type", "ingredient_type"),
        CheckConstraint(
            "verification_status IN "
            "('VERIFIED', 'PROVISIONAL', 'UNVERIFIED', 'REVIEW_REQUIRED')",
            name="ingredient_verification_status_supported",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    ingredient_type: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(2048))
    common_food_applications: Mapped[list[str] | None] = mapped_column(JSON)
    vegetarian_status: Mapped[str | None] = mapped_column(String(24))
    vegan_status: Mapped[str | None] = mapped_column(String(24))
    evidence_quality: Mapped[str] = mapped_column(
        String(32),
        default="unreviewed",
        server_default=text("'unreviewed'"),
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(
        String(24),
        default="REVIEW_REQUIRED",
        server_default=text("'REVIEW_REQUIRED'"),
        nullable=False,
    )
    last_reviewed_at: Mapped[date | None] = mapped_column(Date)

    product_usages: Mapped[list["ProductIngredient"]] = relationship(
        back_populates="ingredient",
        passive_deletes=True,
    )
    aliases: Mapped[list["IngredientAlias"]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    identifiers: Mapped[list["AdditiveIdentifier"]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    categories: Mapped[list["IngredientCategoryLink"]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    functions: Mapped[list["IngredientFunctionLink"]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    allergen_associations: Mapped[list["IngredientAllergen"]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    evidence: Mapped[list["IngredientEvidence"]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    regulatory_references: Mapped[list["IngredientRegulatoryReference"]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class IngredientAlias(Base):
    __tablename__ = "ingredient_aliases"
    __table_args__ = (
        UniqueConstraint("normalized_alias", name="uq_ingredient_aliases_normalized"),
        Index("ix_ingredient_aliases_ingredient_id", "ingredient_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(240), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(240), nullable=False)

    ingredient: Mapped[Ingredient] = relationship(back_populates="aliases")


class AdditiveIdentifier(Base):
    __tablename__ = "additive_identifiers"
    __table_args__ = (
        CheckConstraint(
            "identifier_type IN ('INS', 'E_NUMBER')",
            name="identifier_type_supported",
        ),
        UniqueConstraint(
            "identifier_type",
            "normalized_value",
            name="uq_additive_identifiers_type_value",
        ),
        Index("ix_additive_identifiers_ingredient_id", "ingredient_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        nullable=False,
    )
    identifier_type: Mapped[str] = mapped_column(String(24), nullable=False)
    identifier_value: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(24), nullable=False)

    ingredient: Mapped[Ingredient] = relationship(back_populates="identifiers")


class IngredientCategory(Base):
    __tablename__ = "ingredient_categories"
    __table_args__ = (
        UniqueConstraint("normalized_name", name="uq_ingredient_categories_normalized"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(80), nullable=False)

    ingredients: Mapped[list["IngredientCategoryLink"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class IngredientCategoryLink(Base):
    __tablename__ = "ingredient_category_links"
    __table_args__ = (
        Index("ix_ingredient_category_links_category_id", "category_id"),
    )

    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("ingredient_categories.id", ondelete="CASCADE"),
        primary_key=True,
    )

    ingredient: Mapped[Ingredient] = relationship(back_populates="categories")
    category: Mapped[IngredientCategory] = relationship(back_populates="ingredients")


class IngredientFunction(Base):
    __tablename__ = "ingredient_functions"
    __table_args__ = (
        UniqueConstraint("normalized_name", name="uq_ingredient_functions_normalized"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)

    ingredients: Mapped[list["IngredientFunctionLink"]] = relationship(
        back_populates="function",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class IngredientFunctionLink(Base):
    __tablename__ = "ingredient_function_links"
    __table_args__ = (
        Index("ix_ingredient_function_links_function_id", "function_id"),
    )

    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        primary_key=True,
    )
    function_id: Mapped[int] = mapped_column(
        ForeignKey("ingredient_functions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    technological_purpose: Mapped[str | None] = mapped_column(Text)

    ingredient: Mapped[Ingredient] = relationship(back_populates="functions")
    function: Mapped[IngredientFunction] = relationship(back_populates="ingredients")


class AllergenAlias(Base):
    __tablename__ = "allergen_aliases"
    __table_args__ = (
        UniqueConstraint("normalized_alias", name="uq_allergen_aliases_normalized"),
        Index("ix_allergen_aliases_allergen_id", "allergen_id"),
        CheckConstraint(
            "verification_status IN "
            "('VERIFIED', 'PROVISIONAL', 'UNVERIFIED', 'REVIEW_REQUIRED')",
            name="allergen_alias_verification_status_supported",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    allergen_id: Mapped[int] = mapped_column(
        ForeignKey("allergens.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(160), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(24),
        default="REVIEW_REQUIRED",
        server_default=text("'REVIEW_REQUIRED'"),
        nullable=False,
    )

    allergen: Mapped["Allergen"] = relationship(back_populates="aliases")


class IngredientAllergen(Base):
    __tablename__ = "ingredient_allergens"
    __table_args__ = (
        Index("ix_ingredient_allergens_allergen_id", "allergen_id"),
        CheckConstraint(
            "verification_status IN "
            "('VERIFIED', 'PROVISIONAL', 'UNVERIFIED', 'REVIEW_REQUIRED')",
            name="ingredient_allergen_verification_status_supported",
        ),
    )

    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        primary_key=True,
    )
    allergen_id: Mapped[int] = mapped_column(
        ForeignKey("allergens.id", ondelete="CASCADE"),
        primary_key=True,
    )
    association_type: Mapped[str] = mapped_column(
        String(24),
        primary_key=True,
    )
    source_reference: Mapped[str | None] = mapped_column(String(2048))
    verification_status: Mapped[str] = mapped_column(
        String(24),
        default="REVIEW_REQUIRED",
        server_default=text("'REVIEW_REQUIRED'"),
        nullable=False,
    )

    ingredient: Mapped[Ingredient] = relationship(
        back_populates="allergen_associations"
    )
    allergen: Mapped["Allergen"] = relationship(back_populates="ingredients")


class IngredientEvidence(Base):
    __tablename__ = "ingredient_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_classification IN "
            "('established', 'context_dependent', 'uncertain', 'unverified')",
            name="evidence_classification_supported",
        ),
        Index("ix_ingredient_evidence_ingredient_id", "ingredient_id"),
        Index("ix_ingredient_evidence_classification", "evidence_classification"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        nullable=False,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(240))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    publication_date: Mapped[date | None] = mapped_column(Date)
    limitations: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_at: Mapped[date | None] = mapped_column(Date)

    ingredient: Mapped[Ingredient] = relationship(back_populates="evidence")


class IngredientRegulatoryReference(Base):
    __tablename__ = "ingredient_regulatory_references"
    __table_args__ = (
        Index("ix_ingredient_regulatory_references_ingredient_id", "ingredient_id"),
        Index("ix_ingredient_regulatory_references_jurisdiction", "jurisdiction"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        nullable=False,
    )
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False)
    framework: Mapped[str] = mapped_column(String(200), nullable=False)
    regulatory_status: Mapped[str | None] = mapped_column(String(80))
    usage_conditions: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(String(240))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    reviewed_at: Mapped[date | None] = mapped_column(Date)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ingredient: Mapped[Ingredient] = relationship(
        back_populates="regulatory_references"
    )


class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    __table_args__ = (
        CheckConstraint(
            "ingredient_order >= 0",
            name="ingredient_order_nonnegative",
        ),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ingredient_order: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    original_label_text: Mapped[str] = mapped_column(Text, nullable=False)

    product: Mapped[Product] = relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient] = relationship(back_populates="product_usages")


class ProductNutrient(Base):
    __tablename__ = "product_nutrients"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_nonnegative"),
        UniqueConstraint(
            "product_id",
            "nutrient_name",
            "basis",
            name="uq_product_nutrients_product_name_basis",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    nutrient_name: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    basis: Mapped[NutrientBasis] = mapped_column(
        SAEnum(
            NutrientBasis,
            values_callable=lambda enum_type: [item.value for item in enum_type],
            native_enum=False,
            create_constraint=True,
            name="nutrient_basis_values",
        ),
        nullable=False,
    )

    product: Mapped[Product] = relationship(back_populates="nutrients")
