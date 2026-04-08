"""Slack mention parsing for manager onboarding."""

import pytest

from vector.domains.manager_onboarding import service as mo_service
from vector.domains.manager_onboarding.service import (
    _human_channel_access_message,
    channel_mentions_with_labels,
    extract_plain_hash_channel_names,
    extract_slack_tokens,
    normalize_slack_conversation_id,
    resolve_channel_names_to_ids,
)


def test_extract_public_and_private_channel_ids() -> None:
    text = "See <#C0123ABCD|general> and <#G0999ZZZZ|secret>"
    u, c, rem = extract_slack_tokens(text)
    assert u == []
    assert c == ["C0123ABCD", "G0999ZZZZ"]
    assert "general" not in rem


def test_channel_mentions_with_labels_order() -> None:
    text = "x <#C01|general> y <#C01|general>"
    ids, labels = channel_mentions_with_labels(text)
    assert ids == ["C01"]
    assert labels == {"C01": "general"}


def test_channel_mention_lowercase_prefix_normalized() -> None:
    ids, labels = channel_mentions_with_labels("<#c01abc|general>")
    assert ids == ["C01ABC"]
    assert labels == {"C01ABC": "general"}


def test_normalize_slack_conversation_id() -> None:
    assert normalize_slack_conversation_id(" c0123abcd ") == "C0123ABCD"


def test_human_channel_access_uses_hash_names_not_ids() -> None:
    msg = _human_channel_access_message(["CSECRET"], {"CSECRET": "general"})
    assert "#general" in msg
    assert "CSECRET" not in msg


def test_human_channel_access_fallback_without_labels() -> None:
    msg = _human_channel_access_message(["CXXX"], {})
    assert "CXXX" not in msg
    assert "channel" in msg.lower()


def test_skip_observed_channels_not_ok_or_done() -> None:
    """Ensure ok/done are not Q4 skip; only explicit phrases (e.g. skip) opt out."""
    r = mo_service._SKIP_OBSERVED_CHANNELS_RE
    assert r.match("ok") is None
    assert r.match("done") is None
    assert r.match("OK.") is None
    assert r.match("skip") is not None
    assert r.match("SKIP!") is not None
    assert r.match("later") is not None


def test_extract_plain_hash_channel_names() -> None:
    assert extract_plain_hash_channel_names("#general and #social") == ["general", "social"]
    assert extract_plain_hash_channel_names("<#C01|x> #foo") == ["foo"]


def test_resolve_channel_names_to_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    from vector.domains.manager_onboarding import slack_web_api

    def fake_list(_token: str) -> list[dict]:
        return [{"id": "C111", "name": "general"}, {"id": "C222", "name": "social"}]

    monkeypatch.setattr(slack_web_api, "conversations_list_public_private", fake_list)
    ok, bad = resolve_channel_names_to_ids("t", ["general", "social", "ghost"])
    assert ok == ["C111", "C222"]
    assert bad == ["ghost"]
