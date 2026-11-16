"""add food-intelligence profile preferences

Revision ID: c91f024d7a63
Revises: a8f3c12e9b71
Create Date: 2026-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c91f024d7a63"
down_revision: Union[str, Sequence[str], None] = "a8f3c12e9b71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("health_profiles") as batch:
        batch.add_column(sa.Column("dietary_preferences", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("ingredient_exclusions", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("nutrition_goals", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("calorie_goal_kcal", sa.Float(), nullable=True))
        batch.add_column(sa.Column("protein_goal_g", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("health_profiles") as batch:
        batch.drop_column("protein_goal_g")
        batch.drop_column("calorie_goal_kcal")
        batch.drop_column("nutrition_goals")
        batch.drop_column("ingredient_exclusions")
        batch.drop_column("dietary_preferences")
