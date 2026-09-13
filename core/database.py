"""
Core Platform - Database Configuration

Shared database engine and session for all modules.

Supports both SQLite (default, ships with project) and PostgreSQL
(via DATABASE_URL). SQLite is zero-config for local dev; PostgreSQL
is used when DATABASE_URL points at postgres (docker-compose or prod).

SQLite note: SQLAlchemy's default QueuePool does not work with SQLite's
check_same_thread semantics under concurrent tests. We use StaticPool-
friendly args and omit pool_size/max_overflow for SQLite.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

import os

# Load .env in local dev (no effect in Docker where env is injected)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

_raw_db_url = os.getenv(
    "DATABASE_URL",
    "sqlite:///./techcommerce.db",
)
# Normalize Render/Heroku postgres:// -> postgresql+psycopg:// for SQLAlchemy+psycopg3
if _raw_db_url.startswith("postgres://"):
    _raw_db_url = _raw_db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif _raw_db_url.startswith("postgresql://") and "+psycopg" not in _raw_db_url:
    _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
DATABASE_URL = _raw_db_url

connect_args: dict = {}
engine_kwargs: dict = dict(pool_pre_ping=True, future=True)

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    # For in-memory SQLite (tests) reuse same connection; for file SQLite
    # use NullPool so each Session gets its own connection safely.
    if ":memory:" in DATABASE_URL:
        engine_kwargs["poolclass"] = StaticPool
    else:
        engine_kwargs["poolclass"] = NullPool
else:
    # Postgres — tuned pool for gunicorn concurrency
    engine_kwargs.update(pool_size=5, max_overflow=10, pool_recycle=300)

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)
# Log which DB backend is active (without leaking credentials)
try:
    import logging as _logging
    _db_logger = _logging.getLogger("techcommerce.db")
    _safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    _db_logger.info("DB engine: %s (pool_pre_ping=%s)", _safe_url[:80], engine_kwargs.get("pool_pre_ping"))
except Exception:
    pass

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Imports all model modules so Base.metadata is populated.

    Also stamps alembic_version to the current head so that `alembic upgrade head`
    (run by the Docker entrypoint) does not try to re-create tables that already
    exist. This makes SQLite (via create_all) and Postgres (via alembic) coexist
    without the "table already exists" error.
    """
    # Import all models for side-effect registration on Base.metadata
    import core.models.catalog  # noqa: F401
    import core.models.specification  # noqa: F401
    import core.models.commerce  # noqa: F401
    import core.models.user  # noqa: F401
    import core.models.comparison  # noqa: F401
    import core.models.pc_builder  # noqa: F401
    import core.models.advisor  # noqa: F401
    import core.models.rbac  # noqa: F401
    import core.models.operations  # noqa: F401
    import core.models.notification  # noqa: F401
    Base.metadata.create_all(bind=engine)
    # Stamp alembic_version if missing (so alembic doesn't re-run initial migration)
    try:
        from sqlalchemy import text

        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            if row is None:
                conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('64079eff7df2')"))
            elif row[0] != "64079eff7df2":
                # Leave existing stamp alone (future migrations)
                pass
    except Exception:
        pass  # best-effort; don't block startup
