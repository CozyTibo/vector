"""Celery worker entry (`celery -A app.worker worker`)."""

from __future__ import annotations

from app.celery_app import app

__all__ = ["app"]
