"""add pricing_sheet_images table

Revision ID: f6a8b0c2d4e7
Revises: e5f7a9b1c3d6
Create Date: 2026-06-03

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f6a8b0c2d4e7'
down_revision: Union[str, None] = 'e5f7a9b1c3d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pricing_sheet_images',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ps_id', sa.Integer(), sa.ForeignKey('pricing_sheets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(20), nullable=False),
        sa.Column('file_path', sa.String(255), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('uploaded_at', sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('pricing_sheet_images')
