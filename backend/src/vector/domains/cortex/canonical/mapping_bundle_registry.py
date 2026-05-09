"""Phase 03 Step 5 — read mapping bundle registry snapshot for admin (`phase-03-mapping-bundle-registry.md`)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.mapping_registry_metadata import (
    MAPPING_REGISTRY_DOCTRINE_ANCHORS,
    MAPPING_REGISTRY_SURFACE_VERSION,
)
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.infrastructure.db.models.cortex_mapping_bundle_changelog import CortexMappingBundleChangelogEntry
from vector.infrastructure.db.models.cortex_mapping_bundle_compatibility import CortexMappingBundleCompatibilityEdge
from vector.infrastructure.db.models.cortex_mapping_bundle_pin import CortexMappingBundlePin

REGISTRY_RUNTIME_SCHEMA_VERSION: Final[int] = 1


def build_tenant_mapping_registry_public_document(*, db: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Operator JSON: bundles inventory + compatibility edges + tenant pins + changelog (ordered)."""
    bundles = db.scalars(select(CortexMappingBundle).order_by(CortexMappingBundle.bundle_id)).all()
    edges = db.scalars(select(CortexMappingBundleCompatibilityEdge)).all()
    pins = db.scalars(
        select(CortexMappingBundlePin)
        .where(CortexMappingBundlePin.tenant_id == tenant_id)
        .order_by(CortexMappingBundlePin.scope_kind, CortexMappingBundlePin.scope_marker)
    ).all()
    changelog_ids = [b.bundle_id for b in bundles]
    changelog_rows: list[CortexMappingBundleChangelogEntry] = []
    if changelog_ids:
        changelog_rows = db.scalars(
            select(CortexMappingBundleChangelogEntry)
            .where(CortexMappingBundleChangelogEntry.bundle_id.in_(changelog_ids))
            .order_by(
                CortexMappingBundleChangelogEntry.bundle_id,
                CortexMappingBundleChangelogEntry.sequence_number,
            )
        ).all()

    bundle_payload = [
        {
            "bundle_id": b.bundle_id,
            "lifecycle_state": b.lifecycle_state,
            "manifest_hash": b.manifest_hash,
            "owner_team": b.owner_team,
            "title": b.title,
            "notes": b.notes,
            "predecessor_bundle_id": b.predecessor_bundle_id,
            "created_at": b.created_at,
            "updated_at": b.updated_at,
        }
        for b in bundles
    ]
    edge_payload = [
        {
            "from_bundle_id": e.from_bundle_id,
            "to_bundle_id": e.to_bundle_id,
            "edge_kind": e.edge_kind,
            "is_breaking": e.is_breaking,
            "rationale": e.rationale,
            "declared_at": e.declared_at,
        }
        for e in edges
    ]
    pin_payload = [
        {
            "pin_id": p.id,
            "tenant_id": p.tenant_id,
            "bundle_id": p.bundle_id,
            "scope_kind": p.scope_kind,
            "scope_marker": p.scope_marker or "",
            "effective_from": p.effective_from,
            "policy_reference": p.policy_reference,
            "created_at": p.created_at,
        }
        for p in pins
    ]
    changelog_payload = [
        {
            "bundle_id": c.bundle_id,
            "sequence_number": c.sequence_number,
            "summary": c.summary,
            "breaking_classification": c.breaking_classification,
            "artifact_delta": c.artifact_delta,
            "oracle_vector_refs": c.oracle_vector_refs,
            "compatibility_edges_delta": c.compatibility_edges_delta,
            "invalidation_scope": c.invalidation_scope,
            "ci_report_refs": c.ci_report_refs,
            "created_at": c.created_at,
        }
        for c in changelog_rows
    ]

    return {
        "registry_schema_version": REGISTRY_RUNTIME_SCHEMA_VERSION,
        "mapping_registry_surface_version": MAPPING_REGISTRY_SURFACE_VERSION,
        "phase": "03",
        "implementation_step": 5,
        "completed_implementation_steps": [1, 2, 3, 4, 5],
        "name": "phase03_step05_mapping_bundle_registry",
        "tenant_id": str(tenant_id),
        "bundles": bundle_payload,
        "compatibility_edges": edge_payload,
        "pins_for_tenant": pin_payload,
        "changelog_entries": changelog_payload,
        "doctrine_anchors": list(MAPPING_REGISTRY_DOCTRINE_ANCHORS),
    }
