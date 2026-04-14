from unittest.mock import patch

from vector.domains.manager_onboarding.engine.requirements import (
    REQ_PEER_HANDLES,
    REQ_TEAM_MEMBERS,
)
from vector.domains.manager_onboarding.engine.validate import (
    MAX_LLM_ENTITIES_PER_PATCH,
    strip_patch_to_whitelist,
    validate_patch,
)


def test_strip_patch_drops_unknown_keys() -> None:
    raw = {"team_scope": "ok", "evil": 1, "_pending_channel_ids": ["C1"]}
    assert strip_patch_to_whitelist(raw) == {"team_scope": "ok"}


def test_max_llm_entities_rejects_large_list() -> None:
    big = ["x"] * (MAX_LLM_ENTITIES_PER_PATCH + 1)
    r = validate_patch(
        {"team_member_slack_ids": big},
        bot_token="x",
        manager_slack_user_id="U12345678",
    )
    assert "team_member_slack_ids" in r.field_errors
    assert "team_member_slack_ids" not in r.validated_patch


def test_empty_peer_list_merged_when_primary_matches() -> None:
    r = validate_patch(
        {"peer_slack_user_ids": []},
        bot_token="tok",
        manager_slack_user_id="U12345678",
        primary_requirement_id=REQ_PEER_HANDLES,
    )
    assert r.validated_patch.get("peer_slack_user_ids") == []
    assert not r.field_errors


def test_empty_peer_list_ignored_when_primary_mismatch() -> None:
    r = validate_patch(
        {"peer_slack_user_ids": []},
        bot_token="tok",
        manager_slack_user_id="U12345678",
        primary_requirement_id=REQ_TEAM_MEMBERS,
    )
    assert "peer_slack_user_ids" not in r.validated_patch


@patch("vector.domains.manager_onboarding.engine.validate.slack_web_api.users_info_raw")
def test_uid_accepted_when_users_info_not_user_not_found(mock_ui: object) -> None:
    mock_ui.return_value = {"ok": False, "error": "ratelimited"}
    r = validate_patch(
        {"team_member_slack_ids": ["U0123456789"]},
        bot_token="tok",
        manager_slack_user_id="U0999999999",
    )
    assert r.validated_patch.get("team_member_slack_ids") == ["U0123456789"]
    assert "team_member_slack_ids" not in r.field_errors


@patch("vector.domains.manager_onboarding.engine.validate.slack_web_api.users_info_raw")
def test_uid_rejected_on_user_not_found(mock_ui: object) -> None:
    mock_ui.return_value = {"ok": False, "error": "user_not_found"}
    r = validate_patch(
        {"team_member_slack_ids": ["U0123456789"]},
        bot_token="tok",
        manager_slack_user_id="U0999999999",
    )
    assert r.field_errors.get("team_member_slack_ids") == "all_unresolvable"


@patch("vector.domains.manager_onboarding.engine.validate.slack_web_api.iter_users_list")
def test_team_member_resolves_unique_first_name(mock_ul: object) -> None:
    mock_ul.return_value = iter(
        [
            {
                "id": "U0TEAMMBR01",
                "name": "victoire",
                "profile": {
                    "display_name": "",
                    "real_name": "Victoire Example",
                    "first_name": "Victoire",
                },
            },
        ]
    )
    r = validate_patch(
        {"team_member_slack_ids": ["Victoire"]},
        bot_token="tok",
        manager_slack_user_id="U0999999999",
    )
    assert r.validated_patch.get("team_member_slack_ids") == ["U0TEAMMBR01"]


@patch("vector.domains.manager_onboarding.engine.validate._resolve_channel_entries")
def test_partial_channel_list_merge(mock_res: object) -> None:
    mock_res.return_value = (["C111"], False, True)
    r = validate_patch(
        {"observed_channel_ids": ["eng", "bad"]},
        bot_token="tok",
        manager_slack_user_id="U12345678",
    )
    assert r.validated_patch.get("observed_channel_ids") == ["C111"]
