"""add payment_methods table and migrate payments.method to FK

Revision ID: 5a7c9d1e3f2b
Revises: 4e2a3b9c8d7f
Create Date: 2026-08-07 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5a7c9d1e3f2b'
down_revision: Union[str, Sequence[str], None] = '4e2a3b9c8d7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    op.create_table('payment_methods',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_payment_method_tenant_name'),
    )
    op.create_index(op.f('ix_payment_methods_tenant_id'), 'payment_methods', ['tenant_id'], unique=False)

    tenant_rows = conn.execute(sa.text("SELECT id FROM tenants")).fetchall()
    methods = ['CASH', 'CARD', 'TRANSFER', 'WALLET', 'OTHER']
    for (tid,) in tenant_rows:
        for m in methods:
            conn.execute(
                sa.text(
                    "INSERT INTO payment_methods (tenant_id, name, is_active, created_at) "
                    "VALUES (:tid, :name, TRUE, NOW()) "
                    "ON CONFLICT (tenant_id, name) DO NOTHING"
                ),
                {"tid": tid, "name": m},
            )

    op.add_column('payments', sa.Column('payment_method_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_payments_payment_method_id'), 'payments', ['payment_method_id'], unique=False)

    conn.execute(sa.text(
        "UPDATE payments p SET payment_method_id = pm.id "
        "FROM payment_methods pm "
        "JOIN sales s ON s.tenant_id = pm.tenant_id "
        "WHERE p.sale_id = s.id AND p.method = pm.name"
    ))

    op.alter_column('payments', 'payment_method_id', nullable=False)
    op.create_foreign_key(None, 'payments', 'payment_methods', ['payment_method_id'], ['id'], ondelete='RESTRICT')

    conn.execute(sa.text("ALTER TABLE payments ALTER COLUMN method TYPE VARCHAR(50) USING method::text"))

    conn.execute(sa.text("DROP TYPE IF EXISTS payment_method CASCADE"))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text(
        "CREATE TYPE payment_method AS ENUM ('CASH', 'CARD', 'TRANSFER', 'WALLET', 'OTHER')"
    ))
    conn.execute(sa.text("ALTER TABLE payments ALTER COLUMN method TYPE payment_method USING method::payment_method"))

    op.drop_constraint(None, 'payments', type_='foreignkey')
    op.drop_column('payments', 'payment_method_id')
    op.drop_index(op.f('ix_payments_payment_method_id'), table_name='payments')

    op.drop_index(op.f('ix_payment_methods_tenant_id'), table_name='payment_methods')
    op.drop_table('payment_methods')
