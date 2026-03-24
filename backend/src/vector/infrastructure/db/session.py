"""SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from vector.settings import get_settings

_engine: Any = None
_session_factory: sessionmaker[Session] | None = None


def _configure_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        return
    settings = get_settings()
    _engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )
    _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_engine() -> Any:
    _configure_engine()
    assert _engine is not None
    return _engine


def session_scope() -> Generator[Session, None, None]:
    _configure_engine()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_session_dependency() -> Generator[Session, None, None]:
    """FastAPI dependency: one transaction per request."""
    _configure_engine()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
