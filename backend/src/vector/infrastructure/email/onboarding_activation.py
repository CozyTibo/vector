"""Email sent when an admin moves a workspace from waitlist to onboarding (workspace access enabled)."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from vector.infrastructure.email.envelope import EmailEnvelope
from vector.infrastructure.email.smtp_send import send_email_smtp
from vector.settings import Settings, get_settings

_logger = logging.getLogger("app.email")

_DIR = Path(__file__).resolve().parent
# RFC 5322 Subject (no em dash); must match product copy.
_SUBJECT = "Your Vector workspace is ready: Start onboarding!"

_PERSONAL_NOTE = (
    "Great news! I've activated your workspace. "
    "You can jump into my onboarding whenever you're ready; it only takes a few minutes."
)


def _first_name(full_name: str | None) -> str | None:
    if full_name is None:
        return None
    s = str(full_name).strip()
    if not s:
        return None
    return s.split()[0]


def onboarding_entry_url(settings: Settings) -> str:
    """Public product URL for the onboarding flow (same host as FRONTEND_URL)."""
    return f"{settings.frontend_url.rstrip('/')}/app/onboarding"


def _template_env(*, autoescape: bool) -> Environment:
    return Environment(
        loader=FileSystemLoader(_DIR / "templates"),
        autoescape=autoescape,
    )


def _logo_url(settings: Settings) -> str:
    """Use the same public logo asset as the homepage branding."""
    return f"{settings.frontend_url.rstrip('/')}/logo.jpeg"


def render_onboarding_activation_email(
    *,
    onboarding_url: str,
    full_name: str | None,
    logo_url: str,
) -> tuple[str, str]:
    """Return ``(body_text, body_html)``."""
    fn = _first_name(full_name)
    ctx = {
        "first_name": fn,
        "personal_note": _PERSONAL_NOTE,
        "onboarding_url": onboarding_url,
        "logo_url": logo_url,
    }
    text = _template_env(autoescape=False).get_template("onboarding_activation.txt.j2").render(**ctx)
    html = _template_env(autoescape=True).get_template("onboarding_activation.html.j2").render(**ctx)
    return text, html


def send_onboarding_activation_email(
    settings: Settings,
    *,
    to: str,
    full_name: str | None,
    onboarding_url: str,
) -> None:
    """Send onboarding activation email (raises if SMTP misconfigured)."""
    if not settings.email_is_configured:
        _logger.warning("onboarding activation email skipped (SMTP not configured): to=%s", to[:120])
        return
    if not settings.onboarding_activation_email_enabled:
        _logger.warning(
            "onboarding activation email skipped (VECTOR_ONBOARDING_ACTIVATION_EMAIL=false): to=%s",
            to[:120],
        )
        return
    _logger.debug("onboarding activation email to=%s", to[:120])
    body_text, body_html = render_onboarding_activation_email(
        onboarding_url=onboarding_url,
        full_name=full_name,
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


def enqueue_onboarding_activation_email(
    *,
    to: str,
    full_name: str | None,
    onboarding_url: str,
) -> str | None:
    """Queue onboarding activation on Celery. Returns task id, or ``None`` if email is disabled."""
    settings = get_settings()
    if not settings.email_is_configured:
        _logger.warning("onboarding activation email skipped (not configured): to=%s", to[:120])
        return None
    if not settings.onboarding_activation_email_enabled:
        _logger.debug(
            "onboarding activation email skipped (VECTOR_ONBOARDING_ACTIVATION_EMAIL=false): to=%s",
            to[:120],
        )
        return None

    from app.tasks.onboarding_activation_task import send_onboarding_activation_email_task

    async_result = send_onboarding_activation_email_task.delay(
        {
            "to": to,
            "full_name": full_name,
            "onboarding_url": onboarding_url,
        },
    )
    return str(async_result.id)
