from __future__ import annotations

from vector.domains.cortex.identity.materialize import classify_identity_kind


def test_classify_identity_kind_provider_bot() -> None:
    kind, reason = classify_identity_kind(
        handles={"dependabotbot"},
        display_names=set(),
        emails={"bot@users.noreply.github.com"},
        signal_is_bot=True,
    )
    assert kind == "bot"
    assert reason == "provider_bot_flag"


def test_classify_identity_kind_human() -> None:
    kind, reason = classify_identity_kind(
        handles={"tibo"},
        display_names={"thibault"},
        emails={"tibo@example.com"},
        signal_is_bot=False,
    )
    assert kind == "human"
    assert reason == "has_human_profile_signals"

