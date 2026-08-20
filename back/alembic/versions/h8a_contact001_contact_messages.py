"""HIH-8: таблица contact_messages

Revision ID: h8a_contact001
Revises: h3a_status001
"""
from alembic import op
import sqlalchemy as sa

revision = "h8a_contact001"
down_revision = "h3a_status001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contact_messages",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True, server_default="new"),
    )


def downgrade() -> None:
    op.drop_table("contact_messages")
