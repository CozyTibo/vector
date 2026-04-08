"""Unit tests for Slack admin transcript label substitution."""

from vector.domains.manager_onboarding.slack_admin_display import (
    collect_slack_channel_ids_from_answers,
    collect_slack_user_ids_from_answers,
    enrich_slack_dm_text_for_admin,
)


def test_enrich_channel_and_user_mentions_with_maps() -> None:
    ch = {"C0AQ8GVTD0D": "#eng-random"}
    u = {"U0AR67MHXLG": "@tibo"}
    text = "Hi <@U0AR67MHXLG> see <#C0AQ8GVTD0D> and (IDs: C0AQ8GVTD0D)"
    out = enrich_slack_dm_text_for_admin(text, channel_labels=ch, user_labels=u)
    assert out == "Hi @tibo see #eng-random and (IDs: #eng-random)"


def test_enrich_preserves_slack_embedded_labels() -> None:
    ch: dict[str, str] = {}
    u: dict[str, str] = {}
    text = "Already <#C123|my-channel> and <@U456|Jane Doe>"
    out = enrich_slack_dm_text_for_admin(text, channel_labels=ch, user_labels=u)
    assert out == "Already my-channel and Jane Doe"


def test_enrich_bare_user_token_in_body() -> None:
    ch: dict[str, str] = {}
    u = {"U0AQ8GZ3S2Z": "@alice"}
    text = "U0AQ8GZ3S2Z"
    out = enrich_slack_dm_text_for_admin(text, channel_labels=ch, user_labels=u)
    assert out == "@alice"


def test_collect_slack_user_ids_uppercases() -> None:
    ans = {"team_member_slack_ids": ["u0aq8gz3s2z"]}
    assert collect_slack_user_ids_from_answers(ans) == {"U0AQ8GZ3S2Z"}


def test_collect_slack_channel_ids_uppercases() -> None:
    ans = {"observed_channel_ids": ["c0aq8gvtd0d", "C0AQQRYQ1UH"]}
    assert collect_slack_channel_ids_from_answers(ans) == {"C0AQ8GVTD0D", "C0AQQRYQ1UH"}


def test_enrich_ids_paren_includes_user_ids() -> None:
    ch = {"C0AQ8GVTD0D": "#eng"}
    u = {"U0AQ8GZ3S2Z": "@alice"}
    text = "(IDs: C0AQ8GVTD0D, U0AQ8GZ3S2Z)"
    out = enrich_slack_dm_text_for_admin(text, channel_labels=ch, user_labels=u)
    assert out == "(IDs: #eng, @alice)"
