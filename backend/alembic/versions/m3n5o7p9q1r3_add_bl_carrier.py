"""add carrier to shipment_bls

Revision ID: m3n5o7p9q1r3
Revises: l2m4n6o8p0q2
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa


revision = "m3n5o7p9q1r3"
down_revision = "l2m4n6o8p0q2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shipment_bls", sa.Column("carrier", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("shipment_bls", "carrier")
