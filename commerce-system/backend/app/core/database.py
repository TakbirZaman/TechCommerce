"""
SQLAlchemy engine, session factory, and declarative base.

The commerce service owns its own tables (cart, order, payment, invoice, etc.)
but reads from core-platform-owned tables (users, products, categories, ...)
via SQLAlchemy models that map to the SAME database/schema. This assumes
commerce and core-platform share one Postgres database in this monorepo
setup. If they are split into separate services/databases later, replace
the stub models in app/models/core_platform_stubs.py with an HTTP/gRPC
client instead of direct joins.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
