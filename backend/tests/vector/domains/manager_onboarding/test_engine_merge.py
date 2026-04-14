from vector.domains.manager_onboarding.constants import SCOPE_JUST_ME, SCOPE_OTHER_MANAGERS
from vector.domains.manager_onboarding.engine.merge import merge_validated_patch


def test_merge_scope_just_me_clears_peers() -> None:
    base = {
        "scope_intent": SCOPE_OTHER_MANAGERS,
        "peer_slack_user_ids": ["U1", "U2"],
        "team_scope": "t",
    }
    out = merge_validated_patch(base, {"scope_intent": SCOPE_JUST_ME})
    assert out["peer_slack_user_ids"] == []


def test_merge_reports_no_clears_chain() -> None:
    base = {
        "scope_intent": SCOPE_JUST_ME,
        "team_scope": "t",
        "team_member_slack_ids": ["U1"],
        "observed_channel_ids": ["C1"],
        "reports_to_yes": True,
        "reports_to_slack_ids": ["U9"],
        "kpi_expectations": "x",
    }
    out = merge_validated_patch(base, {"reports_to_yes": False})
    assert out["reports_to_yes"] is False
    assert out["reports_to_slack_ids"] == []


def test_merge_observed_skip_clears_channels() -> None:
    base = {
        "scope_intent": SCOPE_JUST_ME,
        "team_scope": "t",
        "team_member_slack_ids": ["U1"],
        "observed_channel_ids": ["C1"],
        "observed_channels_skipped": False,
        "_pending_channel_ids": ["C9"],
    }
    out = merge_validated_patch(base, {"observed_channels_skipped": True})
    assert out["observed_channels_skipped"] is True
    assert out["observed_channel_ids"] == []
    assert out["_pending_channel_ids"] == []
