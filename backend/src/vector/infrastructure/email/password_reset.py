"""Password reset email."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from vector.infrastructure.email.smtp_send import send_email_smtp
from vector.infrastructure.email.envelope import EmailEnvelope
from vector.settings import Settings, get_settings

_logger = logging.getLogger("app.email")

_DIR = Path(__file__).resolve().parent

_SUBJECT = "Reset your Vector password"


def _template_env(*, autoescape: bool) -> Environment:
    return Environment(
        loader=FileSystemLoader(_DIR / "templates"),
        autoescape=autoescape,
    )


def _logo_url(settings: Settings) -> str:
    """Use the same public logo asset as the homepage branding."""
    return f"{settings.frontend_url.rstrip('/')}/logo.jpeg"


def render_password_reset_email(
    *,
    reset_url: str,
    email_hint: str,
    ttl_hours: int,
    logo_url: str,
) -> tuple[str, str]:
    """Return ``(body_text, body_html)``."""
    ctx = {
        "reset_url": reset_url,
        "email_hint": email_hint,
        "ttl_hours": ttl_hours,
        "logo_url": logo_url,
    }
    text = _template_env(autoescape=False).get_template("password_reset.txt.j2").render(**ctx)
    html = _template_env(autoescape=True).get_template("password_reset.html.j2").render(**ctx)
    return text, html


def send_password_reset_email(
    settings: Settings,
    *,
    to: str,
    reset_url: str,
    email_hint: str,
    ttl_hours: int,
) -> None:
    """Send password reset email (raises if SMTP misconfigured)."""
    if not settings.email_is_configured:
        _logger.warning("password reset email skipped (SMTP not configured): to=%s", to[:120])
        return
    _logger.debug("password reset email to=%s", to[:120])
    body_text, body_html = render_password_reset_email(
        reset_url=reset_url,
        email_hint=email_hint,
        ttl_hours=ttl_hours,
        logo_url=_logo_url(settings),
    )
    send_email_smtp(
        settings,
        EmailEnvelope(
            to=[to],
            subject=_SUBJECT,
            body_text=body_text,
            body_html=body_html,
        ),
    )


def enqueue_password_reset_email(
    *,
    to: str,
    reset_url: str,
    email_hint: str,
    ttl_hours: int,
) -> str | None:
    """Queue password reset on Celery. Returns task id, or ``None`` if email cannot be sent."""
    settings = get_settings()
    if not settings.email_is_configured:
        _logger.warning("password reset email skipped (not configured): to=%s", to[:120])
        return None

    from app.tasks.email import send_password_reset_email_task

    async_result = send_password_reset_email_task.delay(
        {
            "to": to,
            "reset_url": reset_url,
            "email_hint": email_hint,
            "ttl_hours": ttl_hours,
        },
    )
    return str(async_result.id)
