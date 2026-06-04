"""add remarks column to shipments

Revision ID: a1b2c3d4e5f6
Revises: f6a8b0c2d4e7
Create Date: 2026-06-04

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f6a8b0c2d4e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('shipments', sa.Column('remarks', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('shipments', 'remarks')
