"""add accounting_records table

Revision ID: k1l3m5n7o9p1
Revises: j0k2l4m6n8o0
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = 'k1l3m5n7o9p1'
down_revision = 'j0k2l4m6n8o0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'accounting_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(),
                  sa.ForeignKey('formal_orders.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('profit', sa.Numeric(14, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('salary_calculated', sa.Boolean(), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('recorded_by', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('recorded_at', sa.String(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.String(), server_default=sa.text('now()'), nullable=False),
    )


def downgrade():
    op.drop_table('accounting_records')
