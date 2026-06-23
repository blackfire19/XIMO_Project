"""add discharge_country to shipment_bls

Revision ID: o5p7q9r1s3t5
Revises: n4o6p8q0r2s4
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa


revision = "o5p7q9r1s3t5"
down_revision = "n4o6p8q0r2s4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shipment_bls", sa.Column("discharge_country", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("shipment_bls", "discharge_country")
