"""Deterministic identity primitive projection (work object → shared org fingerprint)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from vector.domains.cortex.identity.identity_primitive_projection import (
    extract_identity_primitives,
    org_entity_id_for_identity_primitive,
)


def _slack_anchor_raw(uid: str, cluster: str) -> tuple[object, object]:
    anchor = SimpleNamespace(
        canonical_entity_id=uuid.uuid4(),
        provider_identity_hash="h1",
        canonical_object_kind="message",
        connector="slack",
        raw_record_id=1,
        provider_identity_json={"connector": "slack", "conversation_provider_id": "C:1", "message_provider_id": "1"},
    )
    raw = SimpleNamespace(
        resource_type="slack.message",
        payload_body={
            "user_id": uid,
            "user_email": "a@nexora.test",
            "display_name": "Alex",
            "metadata": {
                "continuity_fixture": {
                    "cluster_key": cluster,
                    "link_subject": "ls:1",
                    "stable_account_key": "stable:1",
                }
            },
        },
    )
    return anchor, raw


def test_two_messages_same_slack_share_primitive_org_id() -> None:
    tid = uuid.uuid4()
    a1, r1 = _slack_anchor_raw("USAME01", "clust-a")
    a2, r2 = _slack_anchor_raw("USAME01", "clust-a")
    p1 = extract_identity_primitives(anchor=a1, raw=r1)[0]
    p2 = extract_identity_primitives(anchor=a2, raw=r2)[0]
    assert p1.projection_kind == "slack_user"
    assert p2.projection_kind == "slack_user"
    assert org_entity_id_for_identity_primitive(tenant_id=tid, projection=p1) == org_entity_id_for_identity_primitive(
        tenant_id=tid,
        projection=p2,
    )


def test_github_extracts_multiple_actor_logins_from_pr() -> None:
    tid = uuid.uuid4()
    anchor = SimpleNamespace(
        canonical_entity_id=uuid.uuid4(),
        provider_identity_hash="h-multi",
        canonical_object_kind="pull_request",
        connector="github",
        raw_record_id=1,
        provider_identity_json={},
    )
    raw = SimpleNamespace(
        resource_type="github.pull_request",
        payload_body={
            "pull_request": {
                "user": {"login": "alice"},
                "assignee": {"login": "bob"},
                "requested_reviewers": [{"login": "charlie"}],
            }
        },
    )
    projs = extract_identity_primitives(anchor=anchor, raw=raw)
    logins = sorted(
        p.identity_material["github_login"] for p in projs if p.projection_kind == "github_user"
    )
    assert logins == ["alice", "bob", "charlie"]
    assert len({org_entity_id_for_identity_primitive(tenant_id=tid, projection=p) for p in projs if p.projection_kind == "github_user"}) == 3


def test_cross_tool_cluster_primitive_distinct_from_slack() -> None:
    tid = uuid.uuid4()
    anchor, raw = _slack_anchor_raw("UX01", "clust-x")
    projs = extract_identity_primitives(anchor=anchor, raw=raw)
    kinds = {p.projection_kind for p in projs}
    assert "slack_user" in kinds
    assert "cross_tool_cluster" in kinds
    slack = next(p for p in projs if p.projection_kind == "slack_user")
    cl = next(p for p in projs if p.projection_kind == "cross_tool_cluster")
    assert org_entity_id_for_identity_primitive(tenant_id=tid, projection=slack) != org_entity_id_for_identity_primitive(
        tenant_id=tid,
        projection=cl,
    )
