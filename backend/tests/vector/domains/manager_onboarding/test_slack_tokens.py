"""Slack mention parsing for manager onboarding."""

from vector.domains.manager_onboarding.service import (
    _human_channel_access_message,
    channel_mentions_with_labels,
    extract_slack_tokens,
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


def test_human_channel_access_uses_hash_names_not_ids() -> None:
    msg = _human_channel_access_message(["CSECRET"], {"CSECRET": "general"})
    assert "#general" in msg
    assert "CSECRET" not in msg


def test_human_channel_access_fallback_without_labels() -> None:
    msg = _human_channel_access_message(["CXXX"], {})
    assert "CXXX" not in msg
    assert "channel" in msg.lower()
