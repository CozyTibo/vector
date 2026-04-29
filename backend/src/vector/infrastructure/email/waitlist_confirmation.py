"""Waitlist signup confirmation email from Vector (personal note + rollout status)."""

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

_PERSONAL_NOTE = (
    "I wanted to reach out personally to confirm you're on the list. "
    "I'll get back to you as soon as we can activate your workspace and walk you through onboarding. "
    "It only takes five minutes!"
)

_WAITLIST_STATUS = (
    "We're onboarding companies in batches as we finish the rollout; "
    "I'll email you with next steps when your workspace is ready."
)

_SUBJECT = "You're on the Vector waitlist"


def _template_env(*, autoescape: bool) -> Environment:
    return Environment(
        loader=FileSystemLoader(_DIR / "templates"),
        autoescape=autoescape,
    )


def render_waitlist_signup_email() -> tuple[str, str]:
    """Return ``(body_text, body_html)``."""
    ctx = {
        "personal_note": _PERSONAL_NOTE,
        "waitlist_status": _WAITLIST_STATUS,
        "avatar_cid": _AVATAR_CID,
    }
    text = _template_env(autoescape=False).get_template("waitlist_signup.txt.j2").render(**ctx)
    html = _template_env(autoescape=True).get_template("waitlist_signup.html.j2").render(**ctx)
    return text, html


def send_waitlist_signup_confirmation(
    settings: Settings,
    *,
    to: str,
    full_name: str | None,
) -> None:
    """Send the waitlist confirmation email (raises if SMTP misconfigured)."""
    if not settings.waitlist_signup_email_enabled:
        _logger.warning("waitlist email skipped (VECTOR_WAITLIST_SIGNUP_EMAIL=false): to=%s", to[:120])
        return
    _logger.debug(
        "waitlist signup email to=%s has_display_name=%s",
        to[:120],
        bool(full_name and full_name.strip()),
    )
    png = _AVATAR_PATH.read_bytes()
    body_text, body_html = render_waitlist_signup_email()
    send_email_smtp_multipart_related(
        settings,
        to=[to],
        subject=_SUBJECT,
        body_text=body_text,
        body_html=body_html,
        inline_png=(_AVATAR_CID, png),
    )


def enqueue_waitlist_signup_confirmation(to: str, full_name: str | None = None) -> str | None:
    """Queue waitlist confirmation on Celery. Returns task id, or ``None`` if email disabled."""
    settings = get_settings()
    if not settings.email_is_configured:
        _logger.warning("waitlist email skipped (not configured): to=%s", to[:120])
        return None
    if not settings.waitlist_signup_email_enabled:
        _logger.debug("waitlist email skipped (VECTOR_WAITLIST_SIGNUP_EMAIL=false): to=%s", to[:120])
        return None

    from app.tasks.email import send_waitlist_signup_confirmation_task

    async_result = send_waitlist_signup_confirmation_task.delay(
        {"to": to, "full_name": full_name},
    )
    task_id: str = async_result.id
    return task_id
