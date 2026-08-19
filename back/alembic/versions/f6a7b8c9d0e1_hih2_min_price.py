"""HIH-2: pictures.min_price

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('pictures', sa.Column('min_price', sa.Float(), nullable=False, server_default='500'))


def downgrade():
    op.drop_column('pictures', 'min_price')
