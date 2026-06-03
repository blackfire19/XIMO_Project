"""redesign products table for inventory import

Revision ID: b2c4d6e8f0a1
Revises: af1309805978
Create Date: 2026-06-03

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c4d6e8f0a1'
down_revision: Union[str, None] = 'af1309805978'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 先删外键约束，再 drop products
    op.drop_constraint('quotation_items_product_id_fkey', 'quotation_items', type_='foreignkey')
    op.drop_constraint('order_items_product_id_fkey', 'order_items', type_='foreignkey')
    op.drop_table('products')
    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('spec', sa.String(length=50), nullable=False),
        sa.Column('material', sa.String(length=50), nullable=False),
        sa.Column('product_type', sa.String(length=50), nullable=False, server_default='无缝钢管'),
        sa.Column('manufacturer', sa.String(length=100), nullable=True),
        sa.Column('warehouse', sa.String(length=20), nullable=False),
        sa.Column('length', sa.String(length=50), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('weight_ton', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('quantity_pcs', sa.Integer(), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('price_updated_at', sa.Date(), nullable=True),
        sa.Column('created_at', sa.String(), server_default='NOW()', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_products_warehouse', 'products', ['warehouse'])
    op.create_index('ix_products_spec', 'products', ['spec'])


def downgrade() -> None:
    op.drop_table('products')
    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('outer_diameter', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('inner_diameter', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('length', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('price_usd', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('material', sa.String(length=100), nullable=True),
        sa.Column('standard', sa.String(length=100), nullable=True),
        sa.Column('surface_finish', sa.String(length=100), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=False, server_default='MT'),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.String(), server_default='NOW()', nullable=False),
        sa.Column('updated_at', sa.String(), server_default='NOW()', nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
