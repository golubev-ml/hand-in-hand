"""add orders table and sold_in_order_id to pictures

Revision ID: b2c3d4e5f6a7
Revises: a1f2b3c4d5e6
Create Date: 2026-08-13
"""
from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1f2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем поле sold_in_order_id в таблицу pictures
    op.add_column("pictures", sa.Column("sold_in_order_id", sa.Integer(), nullable=True, server_default=None))

    # Создаём таблицу orders
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("customer_name", sa.String(100), nullable=False),
        sa.Column("customer_email", sa.String(254), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("payment_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("email_status", sa.String(20), nullable=False, server_default="not_sent"),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_id"), "orders", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_id"), table_name="orders")
    op.drop_table("orders")
    op.drop_column("pictures", "sold_in_order_id")
