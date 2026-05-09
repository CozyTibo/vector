"""Canonical kind invariants governance surface."""

from __future__ import annotations

from vector.domains.cortex.canonical.canonical_kind_invariants import (
    CANONICAL_KIND_INVARIANTS_SCHEMA_VERSION,
    build_canonical_kind_invariants_document,
)


def test_kind_invariants_document_shape_and_required_kinds() -> None:
    doc = build_canonical_kind_invariants_document()
    assert doc["canonical_kind_invariants_schema_version"] == CANONICAL_KIND_INVARIANTS_SCHEMA_VERSION
    kinds = doc["kinds"]
    assert kinds
    ids = {k["kind_id"] for k in kinds}
    required = {
        "document",
        "database_row",
        "message",
        "thread",
        "comment",
        "issue",
        "pull_request",
        "project",
        "cycle",
        "deployment",
        "workflow_run",
        "execution_check",
        "transcript",
        "transcript_segment",
        "person_actor_boundary",
        "container_semantics",
        "relation_semantics",
    }
    assert required.issubset(ids)
    assert len(ids) == len(kinds)

