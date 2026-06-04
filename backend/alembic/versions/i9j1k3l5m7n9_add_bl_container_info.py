"""add container_info to shipment_bls

Revision ID: i9j1k3l5m7n9
Revises: h8i0j2k4l6m8
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa


revision = "i9j1k3l5m7n9"
down_revision = "h8i0j2k4l6m8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shipment_bls", sa.Column("container_info", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("shipment_bls", "container_info")
