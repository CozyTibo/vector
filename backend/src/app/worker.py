"""Celery worker entry (`celery -A app.worker worker`)."""

from __future__ import annotations

import importlib

from app.celery_app import celery_app

importlib.import_module("app.tasks.email")
importlib.import_module("app.tasks.onboarding_activation_task")
importlib.import_module("app.tasks.cortex_ingestion_sync")
importlib.import_module("app.tasks.cortex_ingestion_scheduler")
importlib.import_module("app.tasks.cortex_ingestion_verify")
importlib.import_module("app.tasks.cortex_runtime")

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
        + ". Rebuild the backend image and recreate celery-worker."
    )
    raise RuntimeError(msg)

app = celery_app

__all__ = ["app"]
