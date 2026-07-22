"""add trigramm searching extension

Revision ID: 32796ea4b358
Revises: 458f1f89d91a
Create Date: 2026-07-01 11:07:32.135211

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32796ea4b358'
down_revision: Union[str, Sequence[str], None] = '458f1f89d91a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")