"""merge heads before pos role enum change

Revision ID: 01154f11651c
Revises: e4638b7600eb, 150281b956b0
Create Date: 2026-01-15 13:15:36.513574

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01154f11651c'
down_revision: Union[str, Sequence[str], None] = ('e4638b7600eb', '150281b956b0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
