"""HIH-3: pictures.status_changed_at

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pictures", sa.Column("status_changed_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE pictures SET status_changed_at = sold_at WHERE sold_at IS NOT NULL")


def downgrade():
    op.drop_column("pictures", "status_changed_at")
