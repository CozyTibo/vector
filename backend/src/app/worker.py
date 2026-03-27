"""Celery worker entry (`celery -A app.worker worker`)."""

from __future__ import annotations

import os

from celery import Celery

_redis = os.environ["REDIS_URL"]

app = Celery(
    "vector",
    broker=_redis,
    backend=os.environ.get("CELERY_RESULT_BACKEND", _redis),
)
app.conf.broker_connection_retry_on_startup = True
app.conf.task_default_queue = "vector"
app.conf.task_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_serializer = "json"
