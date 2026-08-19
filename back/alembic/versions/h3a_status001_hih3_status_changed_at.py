"""HIH-3: pictures.status_changed_at

Revision ID: h3a_status001
Revises: h3a_cancel001
"""
from alembic import op
import sqlalchemy as sa

revision = "h3a_status001"
down_revision = "h3a_cancel001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pictures", sa.Column("status_changed_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE pictures SET status_changed_at = sold_at WHERE sold_at IS NOT NULL")


def downgrade():
    op.drop_column("pictures", "status_changed_at")
