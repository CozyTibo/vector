"""Celery worker entry (`celery -A app.worker worker`).

Loads task modules without ``import app.…`` (that would rebind name ``app``
to the package and break the Celery instance).
"""

from __future__ import annotations

import importlib

from app.celery_app import celery_app

importlib.import_module("app.tasks.email")
importlib.import_module("app.tasks.onboarding_activation_task")
importlib.import_module("app.tasks.cortex_ingestion_sync")
importlib.import_module("app.tasks.cortex_ingestion_scheduler")
importlib.import_module("app.tasks.cortex_ingestion_verify")
importlib.import_module("app.tasks.cortex_canon_sync")
importlib.import_module("app.tasks.cortex_canon_scheduler")
importlib.import_module("app.tasks.cortex_identity_sync")
importlib.import_module("app.tasks.cortex_identity_scheduler")

_REQUIRED_EMAIL_TASKS = (
    "vector.email.send",
    "vector.email.waitlist_signup_confirmation",
    "vector.email.password_reset",
    "vector.email.onboarding_activation",
)
_missing = [n for n in _REQUIRED_EMAIL_TASKS if n not in celery_app.tasks]
if _missing:
    msg = (
        "Celery worker is missing task(s): "
        + ", ".join(_missing)
        + ". Rebuild the backend image and recreate celery-worker "
        "(e.g. `docker compose build celery-worker && docker compose up -d --force-recreate celery-worker`)."
    )
    raise RuntimeError(msg)

# Celery CLI (`celery -A app.worker`) expects attribute `app` on this module.
app = celery_app

__all__ = ["app"]
