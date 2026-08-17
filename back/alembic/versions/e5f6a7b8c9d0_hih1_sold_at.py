"""HIH-1: pictures.sold_at

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('pictures', sa.Column('sold_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('pictures', 'sold_at')
