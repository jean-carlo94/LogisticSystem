"""remove DISCONTINUED from product_state enum

Revision ID: 8f1c4d5e6a7b
Revises: 5a7c9d1e3f2b
Create Date: 2026-08-08 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = '8f1c4d5e6a7b'
down_revision: Union[str, Sequence[str], None] = '5a7c9d1e3f2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE product_state RENAME TO product_state_old")
    op.execute("CREATE TYPE product_state AS ENUM ('ACTIVE', 'INACTIVE', 'NO_STOCK')")
    op.execute(
        "ALTER TABLE products ALTER COLUMN state TYPE product_state "
        "USING state::text::product_state"
    )
    op.execute("DROP TYPE product_state_old")


def downgrade() -> None:
    op.execute("ALTER TYPE product_state RENAME TO product_state_new")
    op.execute(
        "CREATE TYPE product_state AS ENUM "
        "('ACTIVE', 'INACTIVE', 'NO_STOCK', 'DISCONTINUED')"
    )
    op.execute(
        "ALTER TABLE products ALTER COLUMN state TYPE product_state "
        "USING state::text::product_state"
    )
    op.execute("DROP TYPE product_state_new")
