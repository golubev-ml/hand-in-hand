"""picture: order_id instead of sold_in_order_id + Pillow version fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-14
"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('pictures', sa.Column('orientation', sa.String(20), server_default='landscape'))
    op.add_column('pictures', sa.Column('image_path_gallery', sa.String(500), server_default=''))
    op.add_column('pictures', sa.Column('image_path_mail', sa.String(500), server_default=''))
    op.add_column('pictures', sa.Column('image_path_mobile', sa.String(500), server_default=''))
    op.add_column('pictures', sa.Column('order_id', sa.Integer(), nullable=True))
    # Переливаем данные из старой колонки, если она есть
    op.execute("UPDATE pictures SET order_id = sold_in_order_id WHERE sold_in_order_id IS NOT NULL")
    op.create_foreign_key('fk_pictures_order_id', 'pictures', 'orders', ['order_id'], ['id'])
    op.drop_column('pictures', 'sold_in_order_id')


def downgrade():
    op.add_column('pictures', sa.Column('sold_in_order_id', sa.Integer()))
    op.execute("UPDATE pictures SET sold_in_order_id = order_id WHERE order_id IS NOT NULL")
    op.drop_constraint('fk_pictures_order_id', 'pictures', type_='foreignkey')
    op.drop_column('pictures', 'order_id')
    op.drop_column('pictures', 'image_path_mobile')
    op.drop_column('pictures', 'image_path_mail')
    op.drop_column('pictures', 'image_path_gallery')
    op.drop_column('pictures', 'orientation')
