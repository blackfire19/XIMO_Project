"""add PI generation fields to quotations, quotation_items, company_info

Revision ID: c3d5e7f9a2b4
Revises: b2c4d6e8f0a1
Create Date: 2026-06-03

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c3d5e7f9a2b4'
down_revision: Union[str, None] = 'b2c4d6e8f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # quotations 新增字段
    op.add_column('quotations', sa.Column('contact_person', sa.String(100), nullable=True))
    op.add_column('quotations', sa.Column('payment_terms', sa.Text(), nullable=True))
    op.add_column('quotations', sa.Column('commodity', sa.String(200), nullable=True))
    op.add_column('quotations', sa.Column('packing', sa.String(100), nullable=True, server_default='EXPORT STANDARD'))
    op.add_column('quotations', sa.Column('port_of_loading', sa.String(200), nullable=True))
    op.add_column('quotations', sa.Column('destination_port', sa.String(200), nullable=True))
    op.add_column('quotations', sa.Column('note_pi', sa.Text(), nullable=True))

    # quotation_items 新增字段
    op.add_column('quotation_items', sa.Column('grade_label', sa.String(50), nullable=True))
    op.add_column('quotation_items', sa.Column('hscode', sa.String(20), nullable=True))

    # company_info 新增字段
    op.add_column('company_info', sa.Column('mobile', sa.String(50), nullable=True))
    op.add_column('company_info', sa.Column('bank_name_full', sa.String(200), nullable=True))
    op.add_column('company_info', sa.Column('bank_code', sa.String(20), nullable=True))
    op.add_column('company_info', sa.Column('bank_address', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('quotations', 'contact_person')
    op.drop_column('quotations', 'payment_terms')
    op.drop_column('quotations', 'commodity')
    op.drop_column('quotations', 'packing')
    op.drop_column('quotations', 'port_of_loading')
    op.drop_column('quotations', 'destination_port')
    op.drop_column('quotations', 'note_pi')

    op.drop_column('quotation_items', 'grade_label')
    op.drop_column('quotation_items', 'hscode')

    op.drop_column('company_info', 'mobile')
    op.drop_column('company_info', 'bank_name_full')
    op.drop_column('company_info', 'bank_code')
    op.drop_column('company_info', 'bank_address')
