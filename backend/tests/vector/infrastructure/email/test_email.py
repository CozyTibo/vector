"""Tests for outbound email envelope and service guards."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from vector.infrastructure.email.envelope import EmailEnvelope
from vector.infrastructure.email.service import send_email_sync
from vector.settings import Settings, get_settings


def test_email_envelope_task_roundtrip() -> None:
    env = EmailEnvelope(
        to=["a@example.com", "b@example.com"],
        subject="Hello",
        body_text="Plain",
        body_html="<p>Hi</p>",
    )
    restored = EmailEnvelope.from_task_payload(env.to_task_payload())
    assert restored == env


def test_send_email_sync_skips_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x:y@localhost:5432/z")
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "")
    get_settings.cache_clear()
    settings = Settings()
    env = EmailEnvelope(to=["u@example.com"], subject="S", body_text="Body")
    assert send_email_sync(settings, env) is False


@patch("vector.infrastructure.email.smtp_send.smtplib.SMTP")
def test_send_email_smtp_sends(mock_smtp: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x:y@localhost:5432/z")
    monkeypatch.setenv("SMTP_HOST", "sandbox.smtp.mailtrap.io")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USER", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "vector@angelcorp.ai")
    monkeypatch.setenv("EMAIL_FROM_NAME", "Vector")
    get_settings.cache_clear()
    settings = Settings()
    env = EmailEnvelope(to=["t@example.com"], subject="Subj", body_text="Hi")
    from vector.infrastructure.email.smtp_send import send_email_smtp

    send_email_smtp(settings, env)

    mock_smtp.assert_called_once_with("sandbox.smtp.mailtrap.io", 2525, timeout=30)
    instance = mock_smtp.return_value.__enter__.return_value
    instance.starttls.assert_called_once()
    instance.login.assert_called_once_with("user", "pass")
    instance.send_message.assert_called_once()
    sent = instance.send_message.call_args[0][0]
    assert sent["Message-ID"]
    assert sent["Date"]
    assert "angelcorp.ai" in sent["Message-ID"]


@patch("vector.infrastructure.email.smtp_send.smtplib.SMTP")
def test_send_email_smtp_multipart_related_sends(
    mock_smtp: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x:y@localhost:5432/z")
    monkeypatch.setenv("SMTP_HOST", "sandbox.smtp.mailtrap.io")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USER", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "vector@angelcorp.ai")
    monkeypatch.setenv("EMAIL_FROM_NAME", "Vector")
    get_settings.cache_clear()
    settings = Settings()
    from vector.infrastructure.email.smtp_send import send_email_smtp_multipart_related

    send_email_smtp_multipart_related(
        settings,
        to=["t@example.com"],
        subject="Subj",
        body_text="Plain",
        body_html='<p><img src="cid:vector_avatar"></p>',
        inline_png=("vector_avatar", b"\x89PNG\r\n\x1a\n"),
    )

    mock_smtp.assert_called_once_with("sandbox.smtp.mailtrap.io", 2525, timeout=30)
    instance = mock_smtp.return_value.__enter__.return_value
    instance.starttls.assert_called_once()
    instance.login.assert_called_once_with("user", "pass")
    instance.send_message.assert_called_once()
    sent = instance.send_message.call_args[0][0]
    assert sent.get_content_type() == "multipart/related"
    raw = sent.as_string()
    assert "vector_avatar" in raw
    assert "image/png" in raw
    assert sent["Message-ID"]
    assert sent["Date"]
    assert "angelcorp.ai" in sent["Message-ID"]


def test_waitlist_signup_email_render() -> None:
    from vector.infrastructure.email.waitlist_confirmation import render_waitlist_signup_email

    text, html = render_waitlist_signup_email()
    assert "Hi 👋" in text
    assert "it only takes five minutes" in text
    assert "onboarding companies in batches" in html
    assert "cid:vector_avatar" in html


def test_email_envelope_rejects_empty_to() -> None:
    with pytest.raises(ValidationError):
        EmailEnvelope(to=[], subject="S", body_text="B")
