"""add unique constraint on pos.phone

Revision ID: 33b4ab6d0c1c
Revises: 799745703a35
Create Date: 2026-01-15 15:17:30.843313

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '33b4ab6d0c1c'
down_revision: Union[str, Sequence[str], None] = '799745703a35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
   op.execute("""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'pos_phone_key'
    ) THEN
        ALTER TABLE pos ADD CONSTRAINT pos_phone_key UNIQUE (phone);
    END IF;
END$$;
""")


def downgrade():
    op.drop_constraint(
        "pos_phone_key",
        "pos",
        type_="unique"
    )
