"""add recipe search indexes

Revision ID: 5143e3c1c147
Revises: 5aaa8eb444e2
Create Date: 2026-06-29 22:23:48.742368

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5143e3c1c147'
down_revision: Union[str, Sequence[str], None] = '5aaa8eb444e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE EXTENSION IF NOT EXISTS pg_trgm"
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_recipes_title_trgm
        ON recipes
        USING gin (title gin_trgm_ops)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ingredients_name_trgm
        ON ingredients
        USING gin (name gin_trgm_ops)
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_ingredients_name_trgm"
    )

    op.execute(
        "DROP INDEX IF EXISTS ix_recipes_title_trgm"
    )
