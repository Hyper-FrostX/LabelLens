import os
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session, sessionmaker


def _normalize_database_url(database_url: str | URL) -> URL:
    url = make_url(database_url) if isinstance(database_url, str) else database_url
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    if url.drivername in {
        "postgresql+psycopg",
        "sqlite",
        "sqlite+pysqlite",
    }:
        return url
    raise ValueError(
        "DATABASE_URL must use PostgreSQL or SQLite with a SQLAlchemy driver."
    )


def get_database_url() -> URL:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required when using database persistence."
        )
    try:
        return _normalize_database_url(database_url)
    except (ArgumentError, TypeError, ValueError) as error:
        raise RuntimeError(
            "DATABASE_URL must be a valid PostgreSQL or SQLite URL."
        ) from error


def build_engine(
    database_url: str | URL | None = None,
    **engine_options,
) -> Engine:
    url = _normalize_database_url(database_url) if database_url else get_database_url()
    options = {"pool_pre_ping": True, **engine_options}
    if url.drivername.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        connect_args.update(options.pop("connect_args", {}))
        options["connect_args"] = connect_args

    engine = create_engine(url, **options)
    if url.drivername.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(connection, _record) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return build_engine()


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    with get_session_factory()() as session:
        yield session


def get_optional_db() -> Generator[Session | None, None, None]:
    if not os.environ.get("DATABASE_URL"):
        yield None
        return
    yield from get_db()
