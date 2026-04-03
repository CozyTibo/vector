"""Celery worker entry (`celery -A app.worker worker`).

Loads ``app.tasks.ingestion`` without ``import app.…`` (that would rebind name ``app``
to the package and break the Celery instance).
"""

from __future__ import annotations

import importlib

from app.celery_app import celery_app

importlib.import_module("app.tasks.ingestion")

# Celery CLI (`celery -A app.worker`) expects attribute `app` on this module.
app = celery_app

__all__ = ["app"]
