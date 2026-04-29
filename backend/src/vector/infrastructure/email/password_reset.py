"""Password reset email — same delivery path as waitlist (multipart + inline avatar)."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from vector.infrastructure.email.smtp_send import send_email_smtp_multipart_related
from vector.settings import Settings, get_settings

_logger = logging.getLogger("app.email")

_DIR = Path(__file__).resolve().parent
_AVATAR_PATH = _DIR / "assets" / "vector-white-bg.png"
_AVATAR_CID = "vector_avatar"

_SUBJECT = "Reset your Vector password"


def _template_env(*, autoescape: bool) -> Environment:
    return Environment(
        loader=FileSystemLoader(_DIR / "templates"),
        autoescape=autoescape,
    )


def render_password_reset_email(
    *,
    reset_url: str,
    email_hint: str,
    ttl_hours: int,
) -> tuple[str, str]:
    """Return ``(body_text, body_html)``."""
    ctx = {
        "reset_url": reset_url,
        "email_hint": email_hint,
        "ttl_hours": ttl_hours,
        "avatar_cid": _AVATAR_CID,
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
    png = _AVATAR_PATH.read_bytes()
    body_text, body_html = render_password_reset_email(
        reset_url=reset_url,
        email_hint=email_hint,
        ttl_hours=ttl_hours,
    )
    send_email_smtp_multipart_related(
        settings,
        to=[to],
        subject=_SUBJECT,
        body_text=body_text,
        body_html=body_html,
        inline_png=(_AVATAR_CID, png),
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
