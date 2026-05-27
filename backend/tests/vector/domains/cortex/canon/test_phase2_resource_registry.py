"""Phase 2 — resource type registry and mapper contracts."""

from __future__ import annotations

import uuid

from vector.domains.cortex.canon.mapper_types import CanonEntityDraft, CanonSourceRef
from vector.domains.cortex.canon.resource_type_registry import (
    disposition_by_resource_type,
    entity_type_for_resource_type,
    registry_rows,
    should_materialize_resource_type,
)


def test_github_pull_request_maps_to_pull_request_entity() -> None:
    assert should_materialize_resource_type("github.pull_request")
    assert entity_type_for_resource_type("github.pull_request") == "pull_request"


def test_slack_reaction_skipped() -> None:
    assert not should_materialize_resource_type("slack.reaction")
    assert entity_type_for_resource_type("slack.reaction") is None


def test_disposition_covers_known_ingest_types() -> None:
    dispositions = disposition_by_resource_type()
    assert dispositions["linear.issue"] == "map"
    assert dispositions["notion.block"] == "map"
    rows = registry_rows()
    assert len(rows) >= 40


def test_canon_entity_draft_frozen_refs() -> None:
    draft = CanonEntityDraft(
        entity_type="message",
        entity_key="k",
        display_label="hi",
        connector="slack",
        connection_id=uuid.uuid4(),
        author_ref="U123",
    )
    assert draft.author_ref == "U123"
    ref = CanonSourceRef(
        raw_id=1,
        connector="slack",
        resource_type="slack.message",
        external_id="C:1",
        source_identity_key="slack:slack.message:C:1",
        source_revision_key="hash:abc",
        observed_at_iso="2026-01-01T00:00:00+00:00",
    )
    assert ref.raw_id == 1
