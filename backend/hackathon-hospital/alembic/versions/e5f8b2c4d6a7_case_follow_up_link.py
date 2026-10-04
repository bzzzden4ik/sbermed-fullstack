"""case follow-up link

Revision ID: e5f8b2c4d6a7
Revises: d4e7a1b2c3f5
Create Date: 2026-10-04 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f8b2c4d6a7'
down_revision: Union[str, Sequence[str], None] = 'd4e7a1b2c3f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('patient_cases') as batch_op:
        batch_op.add_column(sa.Column('related_case_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_patient_cases_related_case_id', 'patient_cases', ['related_case_id'], ['id'], ondelete='SET NULL'
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('patient_cases') as batch_op:
        batch_op.drop_constraint('fk_patient_cases_related_case_id', type_='foreignkey')
        batch_op.drop_column('related_case_id')
