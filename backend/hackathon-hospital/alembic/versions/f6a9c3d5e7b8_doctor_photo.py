"""doctor photo

Revision ID: f6a9c3d5e7b8
Revises: e5f8b2c4d6a7
Create Date: 2026-10-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a9c3d5e7b8'
down_revision: Union[str, Sequence[str], None] = 'e5f8b2c4d6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('doctors', sa.Column('photo_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('doctors') as batch_op:
        batch_op.drop_column('photo_url')
