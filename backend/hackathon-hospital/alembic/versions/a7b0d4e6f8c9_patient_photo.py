"""patient photo

Revision ID: a7b0d4e6f8c9
Revises: f6a9c3d5e7b8
Create Date: 2026-10-05 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b0d4e6f8c9'
down_revision: Union[str, Sequence[str], None] = 'f6a9c3d5e7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('patients', sa.Column('photo_filename', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('patients') as batch_op:
        batch_op.drop_column('photo_filename')
