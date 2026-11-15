"""add ingredient verification statuses and review dates

Revision ID: a8f3c12e9b71
Revises: 7c39e8012a4d
Create Date: 2026-11-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f3c12e9b71"
down_revision: Union[str, Sequence[str], None] = "7c39e8012a4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("ingredients") as batch:
        batch.add_column(
            sa.Column(
                "verification_status",
                sa.String(length=24),
                server_default="REVIEW_REQUIRED",
                nullable=False,
            )
        )
        batch.create_check_constraint(
            "ingredient_verification_status_supported",
            "verification_status IN "
            "('VERIFIED', 'PROVISIONAL', 'UNVERIFIED', 'REVIEW_REQUIRED')",
        )
    with op.batch_alter_table("ingredient_allergens") as batch:
        batch.add_column(
            sa.Column(
                "verification_status",
                sa.String(length=24),
                server_default="REVIEW_REQUIRED",
                nullable=False,
            )
        )
        batch.create_check_constraint(
            "ingredient_allergen_verification_status_supported",
            "verification_status IN "
            "('VERIFIED', 'PROVISIONAL', 'UNVERIFIED', 'REVIEW_REQUIRED')",
        )
    with op.batch_alter_table("allergen_aliases") as batch:
        batch.add_column(
            sa.Column(
                "verification_status",
                sa.String(length=24),
                server_default="REVIEW_REQUIRED",
                nullable=False,
            )
        )
        batch.create_check_constraint(
            "allergen_alias_verification_status_supported",
            "verification_status IN "
            "('VERIFIED', 'PROVISIONAL', 'UNVERIFIED', 'REVIEW_REQUIRED')",
        )
    op.add_column(
        "ingredient_evidence",
        sa.Column("reviewed_at", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ingredient_evidence", "reviewed_at")
    with op.batch_alter_table("allergen_aliases") as batch:
        batch.drop_constraint(
            "allergen_alias_verification_status_supported",
            type_="check",
        )
        batch.drop_column("verification_status")
    with op.batch_alter_table("ingredient_allergens") as batch:
        batch.drop_constraint(
            "ingredient_allergen_verification_status_supported",
            type_="check",
        )
        batch.drop_column("verification_status")
    with op.batch_alter_table("ingredients") as batch:
        batch.drop_constraint(
            "ingredient_verification_status_supported",
            type_="check",
        )
        batch.drop_column("verification_status")
