"""add users created_at index for cursor pagination

Revision ID: 6a1e8d4f2c90
Revises: 3f7c9b2a1d64
Create Date: 2026-08-11 15:25:00.000000

"""
from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '6a1e8d4f2c90'
down_revision: str | None = '3f7c9b2a1d64'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_created_at'), table_name='users')
