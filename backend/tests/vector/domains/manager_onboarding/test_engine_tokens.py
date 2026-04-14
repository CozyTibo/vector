from vector.domains.manager_onboarding.engine.requirements import (
    REQ_CHANNELS,
    REQ_TEAM_MEMBERS,
)
from vector.domains.manager_onboarding.engine.tokens import (
    augment_slack_message_text_with_block_users,
    extract_slack_mrkdwn_entities,
    merge_deterministic_entities_into_patch,
)


def test_extract_user_channel_subteam() -> None:
    text = "Hey <@U0123456789> check <#C0ABCDEFGH|eng> and <!subteam^S0ABCDEFGH|platform>"
    e = extract_slack_mrkdwn_entities(text)
    assert e["user_ids"] == ["U0123456789"]
    assert e["channel_ids"] == ["C0ABCDEFGH"]
    assert e["subteam_tokens"] == ["<!subteam^S0ABCDEFGH|platform>"]


def test_extract_user_mention_case_insensitive() -> None:
    e = extract_slack_mrkdwn_entities("Ping <@u0123456789>")
    assert e["user_ids"] == ["U0123456789"]


def test_augment_text_injects_block_kit_user_ids() -> None:
    blocks = [
        {
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_section",
                    "elements": [
                        {"type": "text", "text": "Hey "},
                        {"type": "user", "user_id": "W0123456789"},
                    ],
                }
            ],
        }
    ]
    out = augment_slack_message_text_with_block_users("", blocks)
    assert "<@W0123456789>" in out
    e = extract_slack_mrkdwn_entities(out)
    assert e["user_ids"] == ["W0123456789"]


def test_merge_unions_llm_patch_and_primary_team_members() -> None:
    raw = {"team_scope": "widgets"}
    out = merge_deterministic_entities_into_patch(
        raw,
        "with <@U1111111111>",
        primary_req_id=REQ_TEAM_MEMBERS,
    )
    assert out["team_member_slack_ids"] == ["U1111111111"]


def test_merge_observed_channels_with_primary_channels() -> None:
    out = merge_deterministic_entities_into_patch(
        {},
        "watch <#CAAAAAAAA>",
        primary_req_id=REQ_CHANNELS,
    )
    assert out["observed_channel_ids"] == ["CAAAAAAAA"]
