from __future__ import annotations

import uuid

from vector.domains.cortex.identity.signals import extract_actor_signal


def test_extract_actor_signal_slack_email_and_name() -> None:
    out = extract_actor_signal(
        canon_entity_id=uuid.uuid4(),
        connector="slack",
        connection_id=uuid.uuid4(),
        entity_key="x",
        external_id="U123",
        source_revision_key="r1",
        payload_body={
            "member": {
                "id": "U123",
                "name": "tibo",
                "is_bot": False,
                "profile": {
                    "email": "TIBO@EXAMPLE.COM",
                    "display_name": "Tibo",
                },
            },
        },
    )
    assert out.emails == {"tibo@example.com"}
    assert "tibo" in out.handles
    assert "tibo" in out.display_names
    assert out.is_bot is not True


def test_extract_actor_signal_github_bot() -> None:
    out = extract_actor_signal(
        canon_entity_id=uuid.uuid4(),
        connector="github",
        connection_id=uuid.uuid4(),
        entity_key="x",
        external_id="42",
        source_revision_key="r1",
        payload_body={"member": {"id": 42, "login": "dependabot[bot]", "type": "Bot"}},
    )
    assert out.is_bot is True
    assert "github_type_bot" in out.bot_reasons
    assert "dependabotbot" in out.handles


def test_extract_actor_signal_slack_deleted_user_not_bot() -> None:
    out = extract_actor_signal(
        canon_entity_id=uuid.uuid4(),
        connector="slack",
        connection_id=uuid.uuid4(),
        entity_key="x",
        external_id="U123",
        source_revision_key="r1",
        payload_body={
            "member": {
                "id": "U123",
                "name": "julien",
                "is_bot": False,
                "deleted": True,
                "profile": {"real_name": "Julien Peyruchat"},
            },
        },
    )
    assert out.is_bot is not True
    assert out.is_inactive is True
    assert "slack_deleted_member" in out.inactive_reasons


def test_extract_actor_signal_notion_adds_name_and_email_local_handles() -> None:
    out = extract_actor_signal(
        canon_entity_id=uuid.uuid4(),
        connector="notion",
        connection_id=uuid.uuid4(),
        entity_key="x",
        external_id="n1",
        source_revision_key="r1",
        payload_body={
            "user": {
                "id": "n1",
                "name": "Julien Peyruchat",
                "person": {"email": "julien.peyruchat@example.com"},
                "type": "person",
            },
        },
    )
    assert "julienpeyruchat" in out.handles

