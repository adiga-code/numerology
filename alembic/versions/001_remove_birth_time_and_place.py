"""Remove birth_time and birth_place columns from order_participants

Revision ID: 001_remove_birth_time_place
Revises:
Create Date: 2026-01-27

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_remove_birth_time_place'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove birth_time and birth_place columns if they exist."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if table exists
    if 'order_participants' not in inspector.get_table_names():
        return

    # Get existing columns
    columns = [col['name'] for col in inspector.get_columns('order_participants')]

    if 'birth_time' in columns:
        op.drop_column('order_participants', 'birth_time')
    if 'birth_place' in columns:
        op.drop_column('order_participants', 'birth_place')


def downgrade() -> None:
    """Re-add birth_time and birth_place columns."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if table exists
    if 'order_participants' not in inspector.get_table_names():
        return

    # Get existing columns
    columns = [col['name'] for col in inspector.get_columns('order_participants')]

    if 'birth_time' not in columns:
        op.add_column('order_participants', sa.Column('birth_time', sa.Time(), nullable=True))
    if 'birth_place' not in columns:
        op.add_column('order_participants', sa.Column('birth_place', sa.String(255), nullable=True))
