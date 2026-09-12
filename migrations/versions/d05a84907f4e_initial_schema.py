"""initial schema

Revision ID: d05a84907f4e
Revises: 
Create Date: 2026-09-12 17:55:36.228464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd05a84907f4e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('customers',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('phone_number', sa.String(length=20), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('balance', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.Column('is_superadmin', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('workstations',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('hourly_rate', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('admin_permissions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('customer_id', sa.String(), nullable=False),
    sa.Column('granted_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('can_manage_admins', sa.Boolean(), nullable=False),
    sa.Column('can_manage_users', sa.Boolean(), nullable=False),
    sa.Column('can_manage_workstations', sa.Boolean(), nullable=False),
    sa.Column('can_manage_billing', sa.Boolean(), nullable=False),
    sa.Column('read_only_billing', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('customer_id')
    )
    op.create_table('sessions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('workstation_id', sa.String(), nullable=False),
    sa.Column('cost', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('start_time', sa.DateTime(), nullable=False),
    sa.Column('end_time', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['customers.id'], ),
    sa.ForeignKeyConstraint(['workstation_id'], ['workstations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_sessions_workstation_id'), 'sessions', ['workstation_id'], unique=False)
    op.create_index('uq_sessions_active_user', 'sessions', ['user_id'], unique=True, sqlite_where=sa.text("status = 'active'"), postgresql_where=sa.text("status = 'active'"))
    op.create_index('uq_sessions_active_workstation', 'sessions', ['workstation_id'], unique=True, sqlite_where=sa.text("status = 'active'"), postgresql_where=sa.text("status = 'active'"))
    op.create_table('transactions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('balance_after', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('note', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['customers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_user_id'), 'transactions', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_transactions_user_id'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index('uq_sessions_active_workstation', table_name='sessions', sqlite_where=sa.text("status = 'active'"), postgresql_where=sa.text("status = 'active'"))
    op.drop_index('uq_sessions_active_user', table_name='sessions', sqlite_where=sa.text("status = 'active'"), postgresql_where=sa.text("status = 'active'"))
    op.drop_index(op.f('ix_sessions_workstation_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_table('admin_permissions')
    op.drop_table('workstations')
    op.drop_table('customers')