"""add pricing_sheets and pricing_sheet_items tables

Revision ID: d4e6f8a0b2c5
Revises: c3d5e7f9a2b4
Create Date: 2026-06-03

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd4e6f8a0b2c5'
down_revision: Union[str, None] = 'c3d5e7f9a2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pricing_sheets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ps_number', sa.String(50), unique=True, nullable=False),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('salesperson_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('trade_terms', sa.String(50), nullable=True),
        sa.Column('currency', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('exchange_rate', sa.Numeric(10, 4), nullable=False),
        sa.Column('sea_freight', sa.Numeric(12, 2), nullable=True),
        sa.Column('tons_per_container', sa.Numeric(10, 3), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('updated_at', sa.String(), nullable=False),
    )
    op.create_table(
        'pricing_sheet_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ps_id', sa.Integer(), sa.ForeignKey('pricing_sheets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('grade_label', sa.String(50), nullable=True),
        sa.Column('hscode', sa.String(20), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Numeric(12, 3), nullable=False, server_default='1'),
        sa.Column('unit', sa.String(20), nullable=False, server_default='MT'),
        sa.Column('cost', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('inland_freight', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('packing_cost', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('port_charges', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('profit', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('calculated_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_table('pricing_sheet_items')
    op.drop_table('pricing_sheets')
