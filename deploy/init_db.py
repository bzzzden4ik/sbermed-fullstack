"""Initialise an EMPTY database: create all tables from the models and stamp Alembic at head.

The historical migration chain cannot build a schema from scratch (some tables were originally
created by Base.metadata.create_all), so fresh databases are created from the models instead.
Later schema changes are applied with `alembic upgrade head` as usual.

Run from backend/hackathon-hospital with the server environment loaded:
    python ../../deploy/init_db.py
"""
import os
import sys

# Run from backend/hackathon-hospital: make the app package importable.
sys.path.insert(0, os.getcwd())

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database import Base, engine
import app.models  # noqa: F401  (registers every table on Base.metadata)


def main() -> int:
    existing = inspect(engine).get_table_names()
    if existing:
        print(f"Database is not empty ({len(existing)} tables, e.g. {', '.join(sorted(existing)[:4])}). "
              "Use `alembic upgrade head` instead. Nothing changed.")
        return 1
    Base.metadata.create_all(bind=engine)
    command.stamp(Config("alembic.ini"), "head")
    tables = sorted(inspect(engine).get_table_names())
    print(f"Created {len(tables)} tables and stamped Alembic at head: {', '.join(tables)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
