"""Tests for reply-step transcript formatting."""

from __future__ import annotations

from dataclasses import dataclass

from vector.domains.manager_onboarding.engine.reply_context import format_recent_messages_transcript


@dataclass
class _FakeMsg:
    direction: str
    text: str


def test_recent_transcript_five_messages() -> None:
    rows = [
        _FakeMsg("outbound", "Hi."),
        _FakeMsg("inbound", "hey"),
        _FakeMsg("outbound", "Team scope?"),
        _FakeMsg("inbound", "Just Victoire"),
        _FakeMsg("outbound", "So just Victoire?"),
        _FakeMsg("inbound", "Yes"),
    ]
    block = format_recent_messages_transcript(rows, current_user_text="Yes", max_messages=5)
    assert "User: hey" in block
    assert "Vector: Team scope?" in block
    assert "User: Just Victoire" in block
    assert "Vector: So just Victoire?" in block
    assert "User: Yes" in block
    assert "Hi." not in block


def test_recent_transcript_empty_rows_uses_current_user() -> None:
    block = format_recent_messages_transcript([], current_user_text="hello")
    assert "User: hello" in block


def test_recent_transcript_shorter_than_five() -> None:
    rows = [
        _FakeMsg("outbound", "Intro."),
        _FakeMsg("inbound", "hi"),
    ]
    block = format_recent_messages_transcript(rows, current_user_text="hi")
    assert "Vector: Intro." in block
    assert "User: hi" in block
