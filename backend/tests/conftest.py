import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import app.models  # noqa: F401
from app.database import Base, build_engine


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    engine = build_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    with Session(db_engine) as session:
        yield session
        session.rollback()


@pytest.fixture(autouse=True)
def disable_external_ai_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "none")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.setenv("DISABLE_GEMINI_VISION", "true")
