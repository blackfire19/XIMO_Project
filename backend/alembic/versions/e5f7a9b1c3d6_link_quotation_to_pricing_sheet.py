"""link quotation to pricing_sheet

Revision ID: e5f7a9b1c3d6
Revises: d4e6f8a0b2c5
Create Date: 2026-06-03

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e5f7a9b1c3d6'
down_revision: Union[str, None] = 'd4e6f8a0b2c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quotations', sa.Column('pricing_sheet_id', sa.Integer(), sa.ForeignKey('pricing_sheets.id'), nullable=True))


def downgrade() -> None:
    op.drop_column('quotations', 'pricing_sheet_id')
