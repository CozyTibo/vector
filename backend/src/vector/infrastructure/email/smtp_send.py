"""SMTP delivery (Mailtrap local, Amazon SES SMTP in production; same code path)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage, Message
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid

from vector.infrastructure.email.envelope import EmailEnvelope
from vector.settings import Settings

_logger = logging.getLogger("app.email")


def _message_id_domain(settings: Settings) -> str:
    """Domain for RFC5322 Message-ID (avoids bare hostname in Docker)."""
    addr = settings.email_from_address.strip()
    if "@" in addr:
        return addr.rsplit("@", 1)[-1]
    return "localhost"


def _apply_standard_headers(root: Message, settings: Settings) -> None:
    """Set Date and Message-ID (many filters penalize if absent)."""
    root["Date"] = formatdate(localtime=True)
    root["Message-ID"] = make_msgid(domain=_message_id_domain(settings))


def send_email_smtp(settings: Settings, envelope: EmailEnvelope) -> None:
    """Send ``envelope`` using configured SMTP. Raises on failure."""
    if not settings.email_is_configured:
        err = "email is not configured (set SMTP_HOST and EMAIL_FROM_ADDRESS)"
        raise RuntimeError(err)

    msg = EmailMessage()
    msg["Subject"] = envelope.subject
    msg["From"] = formataddr((settings.email_from_name, settings.email_from_address))
    msg["To"] = ", ".join(str(a) for a in envelope.to)
    if envelope.reply_to is not None:
        msg["Reply-To"] = str(envelope.reply_to)
    _apply_standard_headers(msg, settings)

    if envelope.body_html is not None:
        msg.set_content(envelope.body_text, charset="utf-8")
        msg.add_alternative(envelope.body_html, subtype="html", charset="utf-8")
    else:
        msg.set_content(envelope.body_text, charset="utf-8")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        user = settings.smtp_user.strip()
        password = settings.smtp_password
        if user or password:
            smtp.login(user, password)
        smtp.send_message(msg)

    _logger.info(
        "email sent subject=%s to=%s",
        envelope.subject[:80],
        [str(a) for a in envelope.to],
    )


def send_email_smtp_multipart_related(
    settings: Settings,
    *,
    to: list[str],
    subject: str,
    body_text: str,
    body_html: str,
    inline_png: tuple[str, bytes],
    reply_to: str | None = None,
) -> None:
    """
    Send HTML + plain text with one inline PNG referenced by ``cid:`` in HTML.

    ``inline_png`` is ``(content_id_without_brackets, raw_png_bytes)`` matching
    ``<img src="cid:content_id_without_brackets">``.
    """
    if not settings.email_is_configured:
        err = "email is not configured (set SMTP_HOST and EMAIL_FROM_ADDRESS)"
        raise RuntimeError(err)

    cid, png_bytes = inline_png
    root = MIMEMultipart("related")
    root["Subject"] = subject
    root["From"] = formataddr((settings.email_from_name, settings.email_from_address))
    root["To"] = ", ".join(to)
    if reply_to is not None:
        root["Reply-To"] = reply_to
    # Date + Message-ID on the outer part before payloads (RFC + spam rules e.g. DOS_BODY_HIGH_NO_MID).
    _apply_standard_headers(root, settings)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_text, "plain", "utf-8"))
    alt.attach(MIMEText(body_html, "html", "utf-8"))
    root.attach(alt)

    image = MIMEImage(png_bytes, _subtype="png")
    image.add_header("Content-ID", f"<{cid}>")
    image.add_header("Content-Disposition", "inline", filename="vector-avatar.png")
    root.attach(image)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        user = settings.smtp_user.strip()
        password = settings.smtp_password
        if user or password:
            smtp.login(user, password)
        smtp.send_message(root)

    _logger.info(
        "email sent (multipart related) subject=%s to=%s cid=%s",
        subject[:80],
        to,
        cid,
    )
