"""add inquiry module (inquiries / formal_orders / files / bls / containers)

Revision ID: g7h9i1j3k5l7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa


revision = "g7h9i1j3k5l7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inquiries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enq_number", sa.String(length=60), nullable=False, unique=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("salesperson_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("deposit_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("deposit_date", sa.Date(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.String(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.String(), server_default=sa.text("NOW()")),
    )
    op.create_table(
        "inquiry_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inquiry_id", sa.Integer(), sa.ForeignKey("inquiries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.String(), server_default=sa.text("NOW()")),
    )
    op.create_table(
        "formal_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("so_number", sa.String(length=60), nullable=False, unique=True),
        sa.Column("inquiry_id", sa.Integer(), sa.ForeignKey("inquiries.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("salesperson_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_stock", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("est_production_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="confirmed"),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.String(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.String(), server_default=sa.text("NOW()")),
    )
    op.create_table(
        "order_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("formal_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(length=20), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.String(), server_default=sa.text("NOW()")),
    )
    op.create_table(
        "shipment_bls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("formal_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ship_type", sa.String(length=20), nullable=False, server_default="container"),
        sa.Column("bl_number", sa.String(length=80), nullable=True),
        sa.Column("vessel_voyage", sa.String(length=120), nullable=True),
        sa.Column("etd", sa.Date(), nullable=True),
        sa.Column("eta", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="planned"),
        sa.Column("pieces", sa.Integer(), nullable=True),
        sa.Column("weight_mt", sa.Numeric(12, 3), nullable=True),
        sa.Column("volume_cbm", sa.Numeric(12, 3), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.String(), server_default=sa.text("NOW()")),
    )
    op.create_table(
        "shipment_containers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bl_id", sa.Integer(), sa.ForeignKey("shipment_bls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("container_type", sa.String(length=20), nullable=True),
        sa.Column("container_number", sa.String(length=50), nullable=True),
        sa.Column("seal_number", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("shipment_containers")
    op.drop_table("shipment_bls")
    op.drop_table("order_files")
    op.drop_table("formal_orders")
    op.drop_table("inquiry_files")
    op.drop_table("inquiries")
