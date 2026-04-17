"""Enqueue or send mail; single entry point for application code."""

from __future__ import annotations

import logging

from vector.infrastructure.email.envelope import EmailEnvelope
from vector.infrastructure.email.smtp_send import send_email_smtp
from vector.settings import Settings, get_settings

_logger = logging.getLogger("app.email")


def send_email_sync(settings: Settings, envelope: EmailEnvelope) -> bool:
    """Send immediately (same process). Returns ``False`` if email is not configured."""
    if not settings.email_is_configured:
        _logger.warning("email skipped (not configured): subject=%s", envelope.subject[:80])
        return False
    send_email_smtp(settings, envelope)
    return True


def enqueue_email(envelope: EmailEnvelope) -> str | None:
    """Queue delivery on the Celery worker. Returns task id, or ``None`` if not configured."""
    settings = get_settings()
    if not settings.email_is_configured:
        _logger.warning("email enqueue skipped (not configured): subject=%s", envelope.subject[:80])
        return None

    from app.tasks.email import send_email_task

    async_result = send_email_task.delay(envelope.to_task_payload())
    return async_result.id


def enqueue_email_or_sync(envelope: EmailEnvelope, *, sync: bool = False) -> str | None:
    """``sync=True`` sends in-process (tests / scripts); else Celery."""
    if sync:
        ok = send_email_sync(get_settings(), envelope)
        return "sync-ok" if ok else None
    return enqueue_email(envelope)
