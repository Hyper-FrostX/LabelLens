from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from alembic import command
from app.database import Base, build_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_initial_migration_upgrades_and_downgrades_sqlite():
    engine = build_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
    )
    try:
        with engine.connect() as connection:
            config = Config(str(BACKEND_DIR / "alembic.ini"))
            config.attributes["connection"] = connection

            command.upgrade(config, "head")
            migrated_tables = set(inspect(connection).get_table_names())
            assert set(Base.metadata.tables).issubset(migrated_tables)
            command.check(config)

            command.downgrade(config, "base")
            remaining_tables = set(inspect(connection).get_table_names())
            assert not set(Base.metadata.tables).intersection(remaining_tables)
    finally:
        engine.dispose()
