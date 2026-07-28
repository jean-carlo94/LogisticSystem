"""add_indexes_and_sale_status_enum

Revision ID: d275f746d875
Revises: d011b94f62e2
Create Date: 2026-07-28 02:23:53.274143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd275f746d875'
down_revision: Union[str, Sequence[str], None] = 'd011b94f62e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_account_activations_token_hash'), 'account_activations', ['token_hash'], unique=False)
    op.create_index(op.f('ix_password_reset_tokens_token_hash'), 'password_reset_tokens', ['token_hash'], unique=False)
    op.create_index(op.f('ix_product_categories_category_id'), 'product_categories', ['category_id'], unique=False)
    op.create_index(op.f('ix_product_categories_product_id'), 'product_categories', ['product_id'], unique=False)
    op.create_index(op.f('ix_role_permissions_permission_id'), 'role_permissions', ['permission_id'], unique=False)
    op.create_index(op.f('ix_role_permissions_role_id'), 'role_permissions', ['role_id'], unique=False)
    op.create_index(op.f('ix_sale_items_product_id'), 'sale_items', ['product_id'], unique=False)
    op.create_index(op.f('ix_sale_items_sale_id'), 'sale_items', ['sale_id'], unique=False)
    op.create_index(op.f('ix_sale_items_shelf_id'), 'sale_items', ['shelf_id'], unique=False)

    sale_status_enum = sa.Enum('COMPLETED', 'CANCELLED', name='sale_status')
    sale_status_enum.create(op.get_bind(), checkfirst=True)
    op.execute("ALTER TABLE sales ALTER COLUMN status TYPE sale_status USING status::sale_status")

    op.create_index(op.f('ix_sales_created_by'), 'sales', ['created_by'], unique=False)
    op.create_index(op.f('ix_shelf_items_product_id'), 'shelf_items', ['product_id'], unique=False)
    op.create_index(op.f('ix_shelf_items_shelf_id'), 'shelf_items', ['shelf_id'], unique=False)
    op.create_index(op.f('ix_user_roles_role_id'), 'user_roles', ['role_id'], unique=False)
    op.create_index(op.f('ix_user_roles_user_id'), 'user_roles', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_roles_user_id'), table_name='user_roles')
    op.drop_index(op.f('ix_user_roles_role_id'), table_name='user_roles')
    op.drop_index(op.f('ix_shelf_items_shelf_id'), table_name='shelf_items')
    op.drop_index(op.f('ix_shelf_items_product_id'), table_name='shelf_items')
    op.drop_index(op.f('ix_sales_created_by'), table_name='sales')
    op.alter_column('sales', 'status',
               existing_type=sa.Enum('COMPLETED', 'CANCELLED', name='sale_status'),
               type_=sa.VARCHAR(length=20),
               existing_nullable=False)
    op.execute("DROP TYPE IF EXISTS sale_status")
    op.drop_index(op.f('ix_sale_items_shelf_id'), table_name='sale_items')
    op.drop_index(op.f('ix_sale_items_sale_id'), table_name='sale_items')
    op.drop_index(op.f('ix_sale_items_product_id'), table_name='sale_items')
    op.drop_index(op.f('ix_role_permissions_role_id'), table_name='role_permissions')
    op.drop_index(op.f('ix_role_permissions_permission_id'), table_name='role_permissions')
    op.drop_index(op.f('ix_product_categories_product_id'), table_name='product_categories')
    op.drop_index(op.f('ix_product_categories_category_id'), table_name='product_categories')
    op.drop_index(op.f('ix_password_reset_tokens_token_hash'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_account_activations_token_hash'), table_name='account_activations')
