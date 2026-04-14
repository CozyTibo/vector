"""ASGI entry for production (`uvicorn app.main:app`)."""

from app.core.logging import setup_logging

setup_logging()

from vector.api.http.main import app

__all__ = ["app"]
