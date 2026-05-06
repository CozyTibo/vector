"""Tests for outbound email envelope and service guards."""

from __future__ import annotations

from pathlib import Path
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

    text, html = render_waitlist_signup_email(logo_url="https://vector.angelcorp.ai/logo.jpeg")
    assert "Hi 👋" in text
    assert "only takes five minutes" in text.lower()
    assert "onboarding companies in batches" in html
    assert "https://vector.angelcorp.ai/logo.jpeg" in html


def test_password_reset_email_render() -> None:
    from vector.infrastructure.email.password_reset import render_password_reset_email

    text, html = render_password_reset_email(
        reset_url="https://app.example/login/reset-password?token=abc",
        email_hint="you@company.com",
        ttl_hours=1,
        logo_url="https://vector.angelcorp.ai/logo.jpeg",
    )
    assert "reset" in text.lower()
    assert "https://app.example/login/reset-password?token=abc" in text
    assert "you@company.com" in html
    assert "Reset password" in html
    assert "https://vector.angelcorp.ai/logo.jpeg" in html


def test_onboarding_activation_subject_no_em_dash() -> None:
    from vector.infrastructure.email import onboarding_activation as oa

    assert "\u2014" not in oa._SUBJECT
    assert oa._SUBJECT == "Your Vector workspace is ready: Start onboarding!"


def test_outbound_email_copy_avoids_unicode_dashes_and_typographic_triggers() -> None:
    """No U+2012–U+2015 in templates; plain text avoids ``---`` (some clients convert it to an em rule)."""
    import vector.infrastructure.email as email_pkg

    root = Path(email_pkg.__path__[0])
    forbidden = "\u2012\u2013\u2014\u2015"
    for path in sorted(root.rglob("*.j2")):
        data = path.read_text(encoding="utf-8")
        for ch in forbidden:
            assert ch not in data, f"{path} must not contain {ch!r}"
        if path.name.endswith(".txt.j2") and "---" in data:
            pytest.fail(f"{path} must not use '---' (auto-typography in some clients)")
    for name in ("waitlist_confirmation.py", "password_reset.py", "onboarding_activation.py"):
        data = (root / name).read_text(encoding="utf-8")
        for ch in forbidden:
            assert ch not in data, f"{name} must not contain {ch!r}"


def test_onboarding_activation_email_render() -> None:
    from vector.infrastructure.email.onboarding_activation import render_onboarding_activation_email

    text, html = render_onboarding_activation_email(
        onboarding_url="https://app.example.com/app/onboarding",
        full_name="Jane Doe",
        logo_url="https://vector.angelcorp.ai/logo.jpeg",
    )
    assert "Hi Jane" in text
    assert "activated your workspace" in text.lower()
    assert "my onboarding" in text.lower()
    assert "https://app.example.com/app/onboarding" in text
    assert "Start onboarding" in html
    assert "https://vector.angelcorp.ai/logo.jpeg" in html


def test_email_envelope_rejects_empty_to() -> None:
    with pytest.raises(ValidationError):
        EmailEnvelope(to=[], subject="S", body_text="B")
