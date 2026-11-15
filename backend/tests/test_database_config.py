import pytest
from sqlalchemy import text

from app.database import build_engine, get_database_url


def test_database_url_is_required_only_when_database_layer_is_used(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        get_database_url()


def test_database_url_normalizes_postgresql_to_psycopg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/label_lens")

    assert get_database_url().drivername == "postgresql+psycopg"


def test_database_url_accepts_sqlite_for_tests(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    assert get_database_url().drivername == "sqlite+pysqlite"


def test_database_url_rejects_unsupported_dialects(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://localhost/label_lens")

    with pytest.raises(RuntimeError, match="PostgreSQL or SQLite"):
        get_database_url()


def test_sqlite_engine_connects_and_enforces_foreign_keys():
    engine = build_engine("sqlite+pysqlite:///:memory:")

    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1
    finally:
        engine.dispose()
