"""Celery tasks for outbound email (SMTP)."""

from __future__ import annotations

import smtplib
from typing import Any

from app.celery_app import celery_app
from vector.infrastructure.email.envelope import EmailEnvelope
from vector.infrastructure.email.smtp_send import send_email_smtp
from vector.infrastructure.email.password_reset import send_password_reset_email
from vector.infrastructure.email.waitlist_confirmation import send_waitlist_signup_confirmation
from vector.settings import get_settings

_TASK_SEND = "vector.email.send"
_TASK_WAITLIST_SIGNUP = "vector.email.waitlist_signup_confirmation"
_TASK_PASSWORD_RESET = "vector.email.password_reset"


@celery_app.task(
    name=_TASK_SEND,
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def send_email_task(payload: dict[str, object]) -> dict[str, str]:
    """Deliver one :class:`~vector.infrastructure.email.envelope.EmailEnvelope`."""
    envelope = EmailEnvelope.from_task_payload(payload)
    settings = get_settings()
    send_email_smtp(settings, envelope)
    return {"status": "sent", "subject": envelope.subject[:200]}


@celery_app.task(
    name=_TASK_WAITLIST_SIGNUP,
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def send_waitlist_signup_confirmation_task(payload: dict[str, Any]) -> dict[str, str]:
    """Send waitlist signup email (HTML + inline avatar); small JSON payload only."""
    to = str(payload["to"])
    full_name = payload.get("full_name")
    full_name_str = str(full_name).strip() if full_name is not None else None
    if full_name_str == "":
        full_name_str = None
    settings = get_settings()
    send_waitlist_signup_confirmation(settings, to=to, full_name=full_name_str)
    return {"status": "sent", "kind": "waitlist_signup"}


@celery_app.task(
    name=_TASK_PASSWORD_RESET,
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def send_password_reset_email_task(payload: dict[str, Any]) -> dict[str, str]:
    """Send password reset email (HTML + inline avatar)."""
    to = str(payload["to"])
    reset_url = str(payload["reset_url"])
    email_hint = str(payload["email_hint"])
    ttl_hours = int(payload["ttl_hours"])
    settings = get_settings()
    send_password_reset_email(
        settings,
        to=to,
        reset_url=reset_url,
        email_hint=email_hint,
        ttl_hours=ttl_hours,
    )
    return {"status": "sent", "kind": "password_reset"}
