from vector.domains.manager_onboarding.engine.conversation_signals import (
    extract_name_like_people_for_primary,
    raw_patch_had_substance,
    should_suppress_entity_block,
)
from vector.domains.manager_onboarding.engine.requirements import REQ_TEAM_MEMBERS


def test_raw_patch_had_substance() -> None:
    assert raw_patch_had_substance({}) is False
    assert raw_patch_had_substance({"team_scope": "x"}) is True
    assert raw_patch_had_substance({"team_member_slack_ids": []}) is False


def test_extract_name_like() -> None:
    assert extract_name_like_people_for_primary(
        {"team_member_slack_ids": ["Victoire", "U0123456789"]},
        REQ_TEAM_MEMBERS,
    ) == ["Victoire"]


def test_suppress_entity_block() -> None:
    assert should_suppress_entity_block(
        merged_something=False,
        entity_unresolved=True,
        soft_names=["Victoire"],
    )
    assert not should_suppress_entity_block(
        merged_something=True,
        entity_unresolved=True,
        soft_names=["Victoire"],
    )
