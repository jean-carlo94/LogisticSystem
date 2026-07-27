"""user_token_version

Revision ID: d011b94f62e2
Revises: edfac29f1a35
Create Date: 2026-07-27 17:14:06.051562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd011b94f62e2'
down_revision: Union[str, Sequence[str], None] = 'edfac29f1a35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.execute("UPDATE users SET token_version = 0")
    op.alter_column("users", "token_version", server_default=None)

    op.drop_constraint("password_reset_tokens_user_id_fkey", "password_reset_tokens", type_="foreignkey")
    op.create_foreign_key(None, "password_reset_tokens", "users", ["user_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("account_activations_user_id_fkey", "account_activations", type_="foreignkey")
    op.create_foreign_key(None, "account_activations", "users", ["user_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("account_activations_user_id_fkey", "account_activations", type_="foreignkey")
    op.create_foreign_key("account_activations_user_id_fkey", "account_activations", "users", ["user_id"], ["id"])

    op.drop_constraint("password_reset_tokens_user_id_fkey", "password_reset_tokens", type_="foreignkey")
    op.create_foreign_key("password_reset_tokens_user_id_fkey", "password_reset_tokens", "users", ["user_id"], ["id"])

    op.drop_column("users", "token_version")
