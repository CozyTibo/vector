"""Deterministic identity primitive projection (work object → shared org fingerprint)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import cast

import pytest

from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.domains.cortex.identity.identity_primitive_projection import (
    aggregate_github_email_extraction_metrics,
    extract_identity_primitives,
    github_emails_for_continuity,
    notion_user_ids_for_continuity,
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


def test_two_messages_same_slack_distinct_org_ids_when_evidence_scoped() -> None:
    tid = uuid.uuid4()
    a1, r1 = _slack_anchor_raw("USAME01", "clust-a")
    a2, r2 = _slack_anchor_raw("USAME01", "clust-b")
    p1 = extract_identity_primitives(anchor=a1, raw=r1)[0]
    p2 = extract_identity_primitives(anchor=a2, raw=r2)[0]
    assert p1.projection_kind == "slack_user"
    assert p2.projection_kind == "slack_user"
    assert p1.identity_material.get("evidence_canonical_entity_id") == str(a1.canonical_entity_id)
    assert p2.identity_material.get("evidence_canonical_entity_id") == str(a2.canonical_entity_id)
    assert org_entity_id_for_identity_primitive(tenant_id=tid, projection=p1) != org_entity_id_for_identity_primitive(
        tenant_id=tid,
        projection=p2,
    )


def test_two_messages_same_slack_share_org_id_when_legacy_fingerprint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_IDENTITY_EVIDENCE_SCOPED_SLACK_GITHUB_FINGERPRINT", "0")
    tid = uuid.uuid4()
    a1, r1 = _slack_anchor_raw("USAME01", "clust-a")
    a2, r2 = _slack_anchor_raw("USAME01", "clust-a")
    p1 = extract_identity_primitives(anchor=a1, raw=r1)[0]
    p2 = extract_identity_primitives(anchor=a2, raw=r2)[0]
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


def test_github_commit_author_and_committer_emails_extracted() -> None:
    anchor = SimpleNamespace(
        canonical_entity_id=uuid.uuid4(),
        provider_identity_hash="h-commit",
        canonical_object_kind="commit",
        connector="github",
        raw_record_id=1,
        provider_identity_json={},
    )
    raw = SimpleNamespace(
        resource_type="github.commit",
        payload_body={
            "commit": {
                "author": {"email": "author@nexora.test", "name": "A"},
                "committer": {"email": "committer@nexora.test", "name": "C"},
            }
        },
    )
    emails = github_emails_for_continuity(raw.payload_body, {})
    assert emails == ["author@nexora.test", "committer@nexora.test"]
    projs = extract_identity_primitives(anchor=anchor, raw=raw)
    email_kinds = [p for p in projs if p.projection_kind in ("email_identity", "email_display_identity")]
    assert len(email_kinds) == 2
    norms = sorted(p.identity_material["email_norm"] for p in email_kinds)
    assert norms == ["author@nexora.test", "committer@nexora.test"]
    metrics = aggregate_github_email_extraction_metrics(
        anchors=[anchor],
        raw_by_id=cast(dict[int, RawIngestionRecord], {1: raw}),
    )
    assert metrics["github_anchors_with_email_primitive"] == 1


def test_notion_page_created_by_projects_notion_user_primitive() -> None:
    tid = uuid.uuid4()
    anchor = SimpleNamespace(
        canonical_entity_id=uuid.uuid4(),
        provider_identity_hash="h-notion",
        canonical_object_kind="page",
        connector="notion",
        raw_record_id=2,
        provider_identity_json={},
    )
    raw = SimpleNamespace(
        resource_type="notion.page",
        payload_body={
            "page": {
                "created_by": {"object": "user", "id": "notion-user-abc", "name": "Pat"},
                "last_edited_by": {"object": "user", "id": "notion-user-abc"},
            }
        },
    )
    assert notion_user_ids_for_continuity(raw.payload_body) == ["notion-user-abc"]
    projs = extract_identity_primitives(anchor=anchor, raw=raw)
    notion = [p for p in projs if p.projection_kind == "notion_user"]
    assert len(notion) == 1
    assert notion[0].identity_material["notion_user_id"] == "notion-user-abc"
    assert notion[0].identity_material.get("display_name") == "Pat"
    assert org_entity_id_for_identity_primitive(tenant_id=tid, projection=notion[0])


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
