"""Registry tests for deterministic canonical → org entity kind mapping."""

from __future__ import annotations

import uuid

from vector.domains.cortex.identity.entity_kind_mapping import (
    public_mapping_registry_snapshot,
    resolve_org_entity_kind_for_anchor,
)
from vector.domains.cortex.identity.org_entities import OrgEntityKind


def test_resolve_person_github() -> None:
    k, rid = resolve_org_entity_kind_for_anchor(
        connector="github",
        canonical_object_kind="person",
        resource_type="github.user",
        provider_login="alice",
    )
    assert k == OrgEntityKind.HUMAN_ACTOR.value
    assert "registry" in rid


def test_resolve_message_slack() -> None:
    k, rid = resolve_org_entity_kind_for_anchor(
        connector="slack",
        canonical_object_kind="message",
        resource_type="slack.message",
        provider_login=None,
    )
    assert k == OrgEntityKind.COORDINATION_THREAD.value
    assert rid.startswith("registry:canonical_kind:")


def test_resolve_bot_login_service_account() -> None:
    k, _ = resolve_org_entity_kind_for_anchor(
        connector="github",
        canonical_object_kind="person",
        resource_type="github.user",
        provider_login="nexora-ci[bot]",
    )
    assert k == OrgEntityKind.SERVICE_ACCOUNT.value


def test_registry_snapshot_stable_keys() -> None:
    snap = public_mapping_registry_snapshot()
    assert snap["entity_kind_mapping_schema_version"] == 1
    assert "person" in snap["canonical_kind_map_keys"]


def test_org_projection_id_matches_primitive_backfill_material() -> None:
    from types import SimpleNamespace

    from vector.domains.cortex.identity.anchor_projection import org_entity_id_for_anchor_row
    from vector.domains.cortex.identity.identity_primitive_projection import (
        extract_identity_primitives,
        org_entity_id_for_identity_primitive,
    )

    tid = uuid.uuid4()
    anchor = SimpleNamespace(
        canonical_entity_id=uuid.uuid4(),
        provider_identity_hash="abc",
        canonical_object_kind="message",
        connector="slack",
        raw_record_id=1,
        provider_identity_json={"connector": "slack", "conversation_provider_id": "C:1", "message_provider_id": "1"},
    )
    raw = SimpleNamespace(resource_type="slack.message", payload_body={"user_id": "U12345", "channel": "C1", "ts": "1"})
    projs = extract_identity_primitives(anchor=anchor, raw=raw)  # type: ignore[arg-type]
    assert projs and projs[0].projection_kind == "slack_user"
    e_prim = org_entity_id_for_identity_primitive(tenant_id=tid, projection=projs[0])
    e_row = org_entity_id_for_anchor_row(tenant_id=tid, anchor=anchor, raw=raw)  # type: ignore[arg-type]
    assert e_prim == e_row
    assert isinstance(e_row, uuid.UUID)
