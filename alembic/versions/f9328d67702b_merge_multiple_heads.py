"""merge multiple heads

Revision ID: f9328d67702b
Revises: 861d2c2ede71, a8c6ea4dca5a
Create Date: 2026-01-14 20:30:39.627378

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9328d67702b'
down_revision: Union[str, Sequence[str], None] = ('861d2c2ede71', 'a8c6ea4dca5a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
