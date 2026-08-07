"""persistent cash registers

Revision ID: 4e2a3b9c8d7f
Revises: 43bf8e3f4590
Create Date: 2026-08-07 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4e2a3b9c8d7f'
down_revision: Union[str, Sequence[str], None] = '1ae783f7c9c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create cash_registers table
    op.create_table('cash_registers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cash_registers_tenant_id'), 'cash_registers', ['tenant_id'], unique=False)

    # 2. Add nullable cash_register_id colum, backfill, then set NOT NULL
    op.add_column('cash_register_sessions', sa.Column('cash_register_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_cash_register_sessions_cash_register_id'), 'cash_register_sessions', ['cash_register_id'], unique=False)

    # Insert default register per tenant that has sessions
    conn = op.get_bind()
    tenant_rows = conn.execute(sa.text("SELECT DISTINCT tenant_id FROM cash_register_sessions")).fetchall()
    for (tid,) in tenant_rows:
        result = conn.execute(
            sa.text("INSERT INTO cash_registers (tenant_id, name, is_active, created_at, updated_at) VALUES (:tid, 'Caja principal', TRUE, NOW(), NOW()) RETURNING id"),
            {"tid": tid}
        )
        reg_id = result.fetchone()[0]
        conn.execute(
            sa.text("UPDATE cash_register_sessions SET cash_register_id = :rid WHERE tenant_id = :tid AND cash_register_id IS NULL"),
            {"rid": reg_id, "tid": tid}
        )

    # Any remaining sessions without register get a catch-all
    leftover = conn.execute(sa.text("SELECT COUNT(*) FROM cash_register_sessions WHERE cash_register_id IS NULL")).scalar()
    if leftover:
        conn.execute(
            sa.text("INSERT INTO cash_registers (tenant_id, name, is_active, created_at, updated_at) SELECT id, 'Caja principal', TRUE, NOW(), NOW() FROM tenants WHERE id NOT IN (SELECT tenant_id FROM cash_registers) RETURNING id")
        )
        conn.execute(
            sa.text("UPDATE cash_register_sessions cs SET cash_register_id = cr.id FROM cash_registers cr WHERE cs.cash_register_id IS NULL AND cr.tenant_id = cs.tenant_id")
        )

    op.alter_column('cash_register_sessions', 'cash_register_id', nullable=False)
    op.create_foreign_key(None, 'cash_register_sessions', 'cash_registers', ['cash_register_id'], ['id'], ondelete='RESTRICT')

    # 3. Drop name column
    op.drop_column('cash_register_sessions', 'name')


def downgrade() -> None:
    op.add_column('cash_register_sessions', sa.Column('name', sa.String(length=100), nullable=True))
    op.drop_constraint(None, 'cash_register_sessions', type_='foreignkey')
    op.drop_column('cash_register_sessions', 'cash_register_id')
    op.drop_index(op.f('ix_cash_register_sessions_cash_register_id'), table_name='cash_register_sessions')
    op.drop_index(op.f('ix_cash_registers_tenant_id'), table_name='cash_registers')
    op.drop_table('cash_registers')
