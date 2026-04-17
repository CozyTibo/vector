"""Outbound email: SMTP (Mailtrap / SES) + Celery queue."""

from vector.infrastructure.email.envelope import EmailEnvelope
from vector.infrastructure.email.service import (
    enqueue_email,
    enqueue_email_or_sync,
    send_email_sync,
)

__all__ = [
    "EmailEnvelope",
    "enqueue_email",
    "enqueue_email_or_sync",
    "send_email_sync",
]
