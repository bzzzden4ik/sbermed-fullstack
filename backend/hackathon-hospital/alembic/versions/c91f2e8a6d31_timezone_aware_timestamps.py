"""Use timezone-aware UTC timestamps.

Revision ID: c91f2e8a6d31
Revises: 5652f059a28d
Create Date: 2026-10-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c91f2e8a6d31"
down_revision: Union[str, Sequence[str], None] = "5652f059a28d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TIMESTAMP_COLUMNS = {
    "users": ("created_at",),
    "patients": ("created_at",),
    "appointments": ("created_at", "updated_at"),
    "prescriptions": ("created_at",),
    "medical_records": ("uploaded_at",),
    "audit_logs": ("timestamp",),
    "conversations": ("created_at",),
}


def _set_timestamp_timezone(enabled: bool) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    for table_name, column_names in TIMESTAMP_COLUMNS.items():
        if not inspector.has_table(table_name):
            continue

        columns = {column["name"]: column for column in inspector.get_columns(table_name)}
        for column_name in column_names:
            column = columns.get(column_name)
            if column is None or getattr(column["type"], "timezone", False) == enabled:
                continue

            op.alter_column(
                table_name,
                column_name,
                existing_type=column["type"],
                type_=sa.DateTime(timezone=enabled),
                postgresql_using=f'"{column_name}" AT TIME ZONE \'UTC\'',
            )


def upgrade() -> None:
    _set_timestamp_timezone(True)


def downgrade() -> None:
    _set_timestamp_timezone(False)