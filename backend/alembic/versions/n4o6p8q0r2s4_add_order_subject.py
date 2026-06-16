"""add subject to formal_orders

Revision ID: n4o6p8q0r2s4
Revises: m3n5o7p9q1r3
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa


revision = "n4o6p8q0r2s4"
down_revision = "m3n5o7p9q1r3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("formal_orders", sa.Column("subject", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("formal_orders", "subject")
