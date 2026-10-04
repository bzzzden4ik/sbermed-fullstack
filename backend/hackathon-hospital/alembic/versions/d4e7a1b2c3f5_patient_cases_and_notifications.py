"""patient cases and notifications

Revision ID: d4e7a1b2c3f5
Revises: 21c2a57b06d0
Create Date: 2026-10-04 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e7a1b2c3f5'
down_revision: Union[str, Sequence[str], None] = '21c2a57b06d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'patient_cases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=True),
        sa.Column('referred_from_doctor_id', sa.Integer(), nullable=True),
        sa.Column('conversation_id', sa.Integer(), nullable=True),
        sa.Column('complaint', sa.Text(), nullable=False),
        sa.Column('ai_summary', sa.JSON(), nullable=True),
        sa.Column('specialization', sa.String(length=255), nullable=True),
        sa.Column('urgency', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=True),
        sa.Column('doctor_comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['referred_from_doctor_id'], ['doctors.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id'),
    )
    op.create_index(op.f('ix_patient_cases_patient_id'), 'patient_cases', ['patient_id'], unique=False)
    op.create_index(op.f('ix_patient_cases_doctor_id'), 'patient_cases', ['doctor_id'], unique=False)
    op.create_index(op.f('ix_patient_cases_status'), 'patient_cases', ['status'], unique=False)

    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['case_id'], ['patient_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_patient_cases_status'), table_name='patient_cases')
    op.drop_index(op.f('ix_patient_cases_doctor_id'), table_name='patient_cases')
    op.drop_index(op.f('ix_patient_cases_patient_id'), table_name='patient_cases')
    op.drop_table('patient_cases')
