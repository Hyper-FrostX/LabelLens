"""add product data provenance and imported label fields

Revision ID: e74b02c91f8a
Revises: c91f024d7a63
Create Date: 2026-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e74b02c91f8a"
down_revision: Union[str, Sequence[str], None] = "c91f024d7a63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("serving_size_text", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("ingredients_text", sa.Text(), nullable=True))
        batch.add_column(sa.Column("declared_allergens", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("may_contain", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("source_name", sa.String(length=240), nullable=True))
        batch.add_column(sa.Column("source_product_id", sa.String(length=240), nullable=True))
        batch.add_column(sa.Column("source_url", sa.String(length=2048), nullable=True))
        batch.add_column(sa.Column("source_license", sa.String(length=240), nullable=True))
        batch.add_column(sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_unique_constraint(
            "uq_products_source_identity",
            ["source_name", "source_product_id"],
        )
        batch.create_check_constraint(
            "product_source_identity_requires_source_name",
            "source_product_id IS NULL OR source_name IS NOT NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("products") as batch:
        batch.drop_constraint(
            "product_source_identity_requires_source_name",
            type_="check",
        )
        batch.drop_constraint("uq_products_source_identity", type_="unique")
        batch.drop_column("source_updated_at")
        batch.drop_column("source_license")
        batch.drop_column("source_url")
        batch.drop_column("source_product_id")
        batch.drop_column("source_name")
        batch.drop_column("may_contain")
        batch.drop_column("declared_allergens")
        batch.drop_column("ingredients_text")
        batch.drop_column("serving_size_text")
