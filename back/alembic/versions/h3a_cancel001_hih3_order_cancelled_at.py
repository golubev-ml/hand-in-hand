"""HIH-3: orders.cancelled_at

Revision ID: h3a_cancel001
Revises: f6a7b8c9d0e1
"""
from alembic import op
import sqlalchemy as sa

revision = "h3a_cancel001"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("cancelled_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("orders", "cancelled_at")
