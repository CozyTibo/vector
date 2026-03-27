"""ASGI entry for production (`uvicorn app.main:app`)."""

from vector.api.http.main import app

__all__ = ["app"]
