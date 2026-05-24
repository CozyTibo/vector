"""People directory label extraction."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from vector.domains.cortex.identity.people_directory_v1 import (
    _cluster_human_actors,
    _entity_needs_raw_enrichment,
    _extract_entity_labels_v1,
)
from vector.domains.cortex.identity.identity_primitive_projection import (
    extract_identity_primitives,
    identity_primitive_backfill_metadata,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def test_identity_primitive_backfill_metadata_surfaces_human_fields() -> None:
    anchor = SimpleNamespace(
        canonical_entity_id=uuid.uuid4(),
        canonical_object_kind="page",
        connector="notion",
        raw_record_id=42,
        bundle_id="bundle-1",
        provider_identity_json={},
    )
    raw_row = SimpleNamespace(resource_type="notion.page", payload_body={
        "page": {
            "created_by": {
                "object": "user",
                "id": "notion-user-1",
                "name": "Ada Lovelace",
                "person": {"email": "ada@example.com"},
            }
        }
    })
    projection = extract_identity_primitives(anchor=anchor, raw=raw_row)[0]
    meta = identity_primitive_backfill_metadata(
        anchor=anchor,
        raw=raw_row,
        projection=projection,
        backfill_job_id=None,
    )
    assert meta["notion_user_id"] == "notion-user-1"
    assert meta["display_name"] == "Ada Lovelace"
    assert meta["email_norm"] == "ada@example.com"


def test_cluster_unions_entities_with_same_email() -> None:
    tid = uuid.uuid4()
    e1, e2, e3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    entities = {
        e1: {
            "id": str(e1),
            "entity_kind": "human_actor",
            "metadata_json": {"email_norm": "max@example.com", "projection_kind": "email_identity"},
        },
        e2: {
            "id": str(e2),
            "entity_kind": "human_actor",
            "metadata_json": {"email_norm": "max@example.com", "projection_kind": "github_user"},
        },
        e3: {
            "id": str(e3),
            "entity_kind": "human_actor",
            "metadata_json": {"email_norm": "other@example.com", "projection_kind": "email_identity"},
        },
    }
    labels = {
        e1: {"display_name": "Max", "email": "max@example.com"},
        e2: {"display_name": "Max", "email": "max@example.com"},
        e3: {"display_name": "Other", "email": "other@example.com"},
    }

    class _FakeSession:
        def scalars(self, *_args, **_kwargs):
            return _EmptyScalars()

    class _EmptyScalars:
        def all(self):
            return []

    clusters = _cluster_human_actors(
        _FakeSession(),
        tenant_id=tid,
        entity_ids={e1, e2, e3},
        entities_by_id=entities,
        labels_by_entity_id=labels,
    )
    assert len(clusters) == 2
    merged = next(c for c in clusters.values() if e1 in c)
    assert e2 in merged
    assert e3 not in merged


def test_entity_needs_raw_enrichment() -> None:
    assert _entity_needs_raw_enrichment({"display_name": None, "email": "a@b.com"}) is True
    assert _entity_needs_raw_enrichment({"display_name": "Ada", "email": None}) is False


def test_extract_entity_labels_from_metadata_github_login() -> None:
    labels = _extract_entity_labels_v1(
        meta={"projection_kind": "github_user", "github_login": "octocat"},
        raw=None,
        prof={},
    )
    assert labels["display_name"] == "octocat"


def test_extract_entity_labels_from_raw_payload() -> None:
    raw = RawIngestionRecord(
        connector="slack",
        resource_type="slack.message",
        external_id="m1",
        payload_body={
            "user_id": "U123",
            "user_email": "alex@example.com",
            "display_name": "Alex Chen",
        },
    )
    labels = _extract_entity_labels_v1(
        meta={
            "projection_kind": "slack_user",
            "source_anchor_raw_record_id": 1,
            "slack_user_id": "U123",
        },
        raw=raw,
        prof={},
    )
    assert labels["display_name"] == "Alex Chen"
    assert labels["email"] == "alex@example.com"
