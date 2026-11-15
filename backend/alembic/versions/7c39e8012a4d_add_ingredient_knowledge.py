"""add normalized ingredient knowledge base

Revision ID: 7c39e8012a4d
Revises: 211c497a78c0
Create Date: 2026-11-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c39e8012a4d"
down_revision: Union[str, Sequence[str], None] = "211c497a78c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingredients",
        sa.Column("common_food_applications", sa.JSON(), nullable=True),
    )
    op.add_column(
        "ingredients",
        sa.Column("vegetarian_status", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "ingredients",
        sa.Column("vegan_status", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "ingredients",
        sa.Column(
            "evidence_quality",
            sa.String(length=32),
            nullable=False,
            server_default="unreviewed",
        ),
    )
    op.add_column(
        "ingredients",
        sa.Column("last_reviewed_at", sa.Date(), nullable=True),
    )

    op.create_table(
        "ingredient_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=240), nullable=False),
        sa.Column("normalized_alias", sa.String(length=240), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingredient_aliases")),
        sa.UniqueConstraint(
            "normalized_alias",
            name="uq_ingredient_aliases_normalized",
        ),
    )
    op.create_index(
        "ix_ingredient_aliases_ingredient_id",
        "ingredient_aliases",
        ["ingredient_id"],
    )

    op.create_table(
        "additive_identifiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("identifier_type", sa.String(length=24), nullable=False),
        sa.Column("identifier_value", sa.String(length=32), nullable=False),
        sa.Column("normalized_value", sa.String(length=24), nullable=False),
        sa.CheckConstraint(
            "identifier_type IN ('INS', 'E_NUMBER')",
            name=op.f("ck_additive_identifiers_identifier_type_supported"),
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_additive_identifiers")),
        sa.UniqueConstraint(
            "identifier_type",
            "normalized_value",
            name="uq_additive_identifiers_type_value",
        ),
    )
    op.create_index(
        "ix_additive_identifiers_ingredient_id",
        "additive_identifiers",
        ["ingredient_id"],
    )

    op.create_table(
        "ingredient_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingredient_categories")),
        sa.UniqueConstraint(
            "normalized_name",
            name="uq_ingredient_categories_normalized",
        ),
    )
    op.create_table(
        "ingredient_category_links",
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["ingredient_categories.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint(
            "ingredient_id",
            "category_id",
            name=op.f("pk_ingredient_category_links"),
        ),
    )
    op.create_index(
        "ix_ingredient_category_links_category_id",
        "ingredient_category_links",
        ["category_id"],
    )

    op.create_table(
        "ingredient_functions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingredient_functions")),
        sa.UniqueConstraint(
            "normalized_name",
            name="uq_ingredient_functions_normalized",
        ),
    )
    op.create_table(
        "ingredient_function_links",
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("function_id", sa.Integer(), nullable=False),
        sa.Column("technological_purpose", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["function_id"],
            ["ingredient_functions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint(
            "ingredient_id",
            "function_id",
            name=op.f("pk_ingredient_function_links"),
        ),
    )
    op.create_index(
        "ix_ingredient_function_links_function_id",
        "ingredient_function_links",
        ["function_id"],
    )

    op.create_table(
        "allergen_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("allergen_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=160), nullable=False),
        sa.Column("normalized_alias", sa.String(length=160), nullable=False),
        sa.ForeignKeyConstraint(
            ["allergen_id"], ["allergens.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_allergen_aliases")),
        sa.UniqueConstraint(
            "normalized_alias",
            name="uq_allergen_aliases_normalized",
        ),
    )
    op.create_index(
        "ix_allergen_aliases_allergen_id",
        "allergen_aliases",
        ["allergen_id"],
    )

    op.create_table(
        "ingredient_allergens",
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("allergen_id", sa.Integer(), nullable=False),
        sa.Column("association_type", sa.String(length=24), nullable=False),
        sa.Column("source_reference", sa.String(length=2048), nullable=True),
        sa.ForeignKeyConstraint(
            ["allergen_id"], ["allergens.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint(
            "ingredient_id",
            "allergen_id",
            "association_type",
            name=op.f("pk_ingredient_allergens"),
        ),
    )
    op.create_index(
        "ix_ingredient_allergens_allergen_id",
        "ingredient_allergens",
        ["allergen_id"],
    )

    op.create_table(
        "ingredient_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("evidence_classification", sa.String(length=32), nullable=False),
        sa.Column("source_name", sa.String(length=240), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "evidence_classification IN "
            "('established', 'context_dependent', 'uncertain', 'unverified')",
            name=op.f("ck_ingredient_evidence_evidence_classification_supported"),
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingredient_evidence")),
    )
    op.create_index(
        "ix_ingredient_evidence_ingredient_id",
        "ingredient_evidence",
        ["ingredient_id"],
    )
    op.create_index(
        "ix_ingredient_evidence_classification",
        "ingredient_evidence",
        ["evidence_classification"],
    )

    op.create_table(
        "ingredient_regulatory_references",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("framework", sa.String(length=200), nullable=False),
        sa.Column("regulatory_status", sa.String(length=80), nullable=True),
        sa.Column("usage_conditions", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(length=240), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("reviewed_at", sa.Date(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_ingredient_regulatory_references"),
        ),
    )
    op.create_index(
        "ix_ingredient_regulatory_references_ingredient_id",
        "ingredient_regulatory_references",
        ["ingredient_id"],
    )
    op.create_index(
        "ix_ingredient_regulatory_references_jurisdiction",
        "ingredient_regulatory_references",
        ["jurisdiction"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ingredient_regulatory_references_jurisdiction",
        table_name="ingredient_regulatory_references",
    )
    op.drop_index(
        "ix_ingredient_regulatory_references_ingredient_id",
        table_name="ingredient_regulatory_references",
    )
    op.drop_table("ingredient_regulatory_references")
    op.drop_index(
        "ix_ingredient_evidence_classification",
        table_name="ingredient_evidence",
    )
    op.drop_index(
        "ix_ingredient_evidence_ingredient_id",
        table_name="ingredient_evidence",
    )
    op.drop_table("ingredient_evidence")
    op.drop_index(
        "ix_ingredient_allergens_allergen_id",
        table_name="ingredient_allergens",
    )
    op.drop_table("ingredient_allergens")
    op.drop_index("ix_allergen_aliases_allergen_id", table_name="allergen_aliases")
    op.drop_table("allergen_aliases")
    op.drop_index(
        "ix_ingredient_function_links_function_id",
        table_name="ingredient_function_links",
    )
    op.drop_table("ingredient_function_links")
    op.drop_table("ingredient_functions")
    op.drop_index(
        "ix_ingredient_category_links_category_id",
        table_name="ingredient_category_links",
    )
    op.drop_table("ingredient_category_links")
    op.drop_table("ingredient_categories")
    op.drop_index(
        "ix_additive_identifiers_ingredient_id",
        table_name="additive_identifiers",
    )
    op.drop_table("additive_identifiers")
    op.drop_index(
        "ix_ingredient_aliases_ingredient_id",
        table_name="ingredient_aliases",
    )
    op.drop_table("ingredient_aliases")
    op.drop_column("ingredients", "last_reviewed_at")
    op.drop_column("ingredients", "evidence_quality")
    op.drop_column("ingredients", "vegan_status")
    op.drop_column("ingredients", "vegetarian_status")
    op.drop_column("ingredients", "common_food_applications")
