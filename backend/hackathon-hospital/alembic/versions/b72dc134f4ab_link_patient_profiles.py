"""Link patient profiles to user accounts.

Revision ID: b72dc134f4ab
Revises: a16ea904f482
Create Date: 2026-10-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b72dc134f4ab"
down_revision: Union[str, Sequence[str], None] = "a16ea904f482"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Wrap all modifications to the 'patients' table into a batch operation
    with op.batch_alter_table("patients", schema=None) as batch_op:
        # 1. Add the column
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        
        # 2. Create the foreign key constraint
        batch_op.create_foreign_key(
            "fk_patients_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        
        # 3. Create the unique index
        batch_op.create_index("ix_patients_user_id", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_patients_user_id", table_name="patients")
    op.drop_constraint("fk_patients_user_id_users", "patients", type_="foreignkey")
    op.drop_column("patients", "user_id")