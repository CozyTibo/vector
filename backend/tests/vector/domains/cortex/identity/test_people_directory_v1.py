"""People directory label extraction."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from vector.domains.cortex.identity.people_directory_v1 import _extract_entity_labels_v1
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
