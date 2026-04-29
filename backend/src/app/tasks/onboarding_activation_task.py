"""Celery task: onboarding activation email (separate module so workers always register it)."""

from __future__ import annotations

import smtplib
from typing import Any

from app.celery_app import celery_app
from vector.infrastructure.email.onboarding_activation import send_onboarding_activation_email
from vector.settings import get_settings

_TASK_NAME = "vector.email.onboarding_activation"


@celery_app.task(
    name=_TASK_NAME,
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def send_onboarding_activation_email_task(payload: dict[str, Any]) -> dict[str, str]:
    """Send onboarding activation email (HTML + inline avatar)."""
    to = str(payload["to"])
    full_name = payload.get("full_name")
    full_name_str = str(full_name).strip() if full_name is not None else None
    if full_name_str == "":
        full_name_str = None
    onboarding_url = str(payload["onboarding_url"])
    settings = get_settings()
    send_onboarding_activation_email(
        settings,
        to=to,
        full_name=full_name_str,
        onboarding_url=onboarding_url,
    )
    return {"status": "sent", "kind": "onboarding_activation"}
