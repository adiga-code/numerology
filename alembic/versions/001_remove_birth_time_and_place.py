"""Remove birth_time and birth_place columns from order_participants

Revision ID: 001_remove_birth_time_place
Revises:
Create Date: 2026-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_remove_birth_time_place'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove birth_time and birth_place columns."""
    op.drop_column('order_participants', 'birth_time')
    op.drop_column('order_participants', 'birth_place')


def downgrade() -> None:
    """Re-add birth_time and birth_place columns."""
    op.add_column('order_participants', sa.Column('birth_time', sa.Time(), nullable=True))
    op.add_column('order_participants', sa.Column('birth_place', sa.String(255), nullable=True))
