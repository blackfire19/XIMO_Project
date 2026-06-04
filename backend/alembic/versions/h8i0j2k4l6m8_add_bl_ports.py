"""add load_port / discharge_port to shipment_bls

Revision ID: h8i0j2k4l6m8
Revises: g7h9i1j3k5l7
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa


revision = "h8i0j2k4l6m8"
down_revision = "g7h9i1j3k5l7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shipment_bls", sa.Column("load_port", sa.String(length=120), nullable=True))
    op.add_column("shipment_bls", sa.Column("discharge_port", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("shipment_bls", "discharge_port")
    op.drop_column("shipment_bls", "load_port")
