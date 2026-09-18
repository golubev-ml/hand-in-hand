"""HIH-9: таблица settings + поле orders.sber_order_id

Revision ID: h9a_pay001
Revises: h8a_contact001
"""
from alembic import op
import sqlalchemy as sa

revision = "h9a_pay001"
down_revision = "h8a_contact001"
branch_labels = None
depends_on = None

settings_tbl = sa.table(
    "settings",
    sa.column("key", sa.String),
    sa.column("value", sa.String),
    sa.column("updated_by", sa.String),
)


def _tables(inspector) -> list[str]:
    return inspector.get_table_names()


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if "settings" not in _tables(insp):
        op.create_table(
            "settings",
            sa.Column("key", sa.String(length=100), primary_key=True),
            sa.Column("value", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("updated_by", sa.String(length=50), nullable=True),
        )
        # Дефолты флагов: оплата ВЫКЛ (на проде пока нет рисунков), письмо ВКЛ.
        op.bulk_insert(settings_tbl, [
            {"key": "payments_enabled", "value": "false", "updated_by": "migration"},
            {"key": "email_after_purchase", "value": "true", "updated_by": "migration"},
        ])

    if "orders" in _tables(insp):
        cols = {c["name"] for c in insp.get_columns("orders")}
        if "sber_order_id" not in cols:
            op.add_column("orders", sa.Column("sber_order_id", sa.String(length=64), nullable=True))
            op.create_index("ix_orders_sber_order_id", "orders", ["sber_order_id"])


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if "orders" in _tables(insp) and "sber_order_id" in {c["name"] for c in insp.get_columns("orders")}:
        op.drop_index("ix_orders_sber_order_id", table_name="orders")
        op.drop_column("orders", "sber_order_id")

    if "settings" in _tables(insp):
        op.drop_table("settings")
