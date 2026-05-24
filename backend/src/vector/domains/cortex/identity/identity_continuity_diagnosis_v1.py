"""Read-only identity continuity diagnosis (Phase S1.1 — prod bucket + anchor sampling)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import nullslast, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.anchor_continuity_candidates import (
    collect_anchor_continuity_rule_buckets_v1,
    continuity_identity_signals_for_anchor,
    summarize_rule_bucket_maps_v1,
)
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_org_link_candidate_batch import CortexOrgLinkCandidateBatch
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

IDENTITY_CONTINUITY_DIAGNOSIS_SCHEMA_VERSION = 1
_ANCHOR_SAMPLE_PER_CONNECTOR = 10


def _latest_candidate_batch_v1(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any] | None:
    row = session.scalar(
        select(CortexOrgLinkCandidateBatch)
        .where(CortexOrgLinkCandidateBatch.tenant_id == tenant_id)
        .order_by(nullslast(CortexOrgLinkCandidateBatch.created_at.desc()), CortexOrgLinkCandidateBatch.id.asc())
        .limit(1)
    )
    if row is None:
        return None
    return {
        "batch_id": str(row.id),
        "candidate_set_sha256": row.candidate_set_sha256,
        "anchor_evidence_input_sha256": row.anchor_evidence_input_sha256,
        "candidate_count": int(row.candidate_count or 0),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "link_rule_version_id": str(row.link_rule_version_id) if row.link_rule_version_id else None,
    }


def _sample_anchors_by_connector_v1(
    anchors: list[CortexCanonicalIdentityAnchor],
    raw_by_id: dict[int, RawIngestionRecord],
    *,
    per_connector: int = _ANCHOR_SAMPLE_PER_CONNECTOR,
) -> dict[str, list[dict[str, Any]]]:
    by_connector: dict[str, list[CortexCanonicalIdentityAnchor]] = defaultdict(list)
    for anchor in sorted(anchors, key=lambda a: (str(a.connector or ""), str(a.id))):
        connector = (anchor.connector or "unknown").strip().lower() or "unknown"
        if len(by_connector[connector]) >= per_connector:
            continue
        by_connector[connector].append(anchor)

    out: dict[str, list[dict[str, Any]]] = {}
    for connector in sorted(by_connector.keys()):
        samples: list[dict[str, Any]] = []
        for anchor in by_connector[connector]:
            raw = raw_by_id.get(int(anchor.raw_record_id))
            signals = continuity_identity_signals_for_anchor(anchor=anchor, raw=raw)
            samples.append(
                {
                    "anchor_id": str(anchor.id),
                    "canonical_entity_id": str(anchor.canonical_entity_id),
                    "canonical_object_kind": anchor.canonical_object_kind,
                    "raw_record_id": int(anchor.raw_record_id),
                    "continuity_identity_signals": signals,
                }
            )
        out[connector] = samples
    return out


def _anchor_counts_by_connector_v1(anchors: list[CortexCanonicalIdentityAnchor]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for anchor in anchors:
        connector = (anchor.connector or "unknown").strip().lower() or "unknown"
        counts[connector] += 1
    return dict(sorted(counts.items()))


def build_identity_continuity_diagnosis_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant-level read-only diagnosis: bucket stats, anchor samples, latest candidate batch."""
    rule_phases, anchors, raw_by_id = collect_anchor_continuity_rule_buckets_v1(session, tenant_id=tenant_id)
    bucket_diagnosis = summarize_rule_bucket_maps_v1(rule_phases)
    latest_batch = _latest_candidate_batch_v1(session, tenant_id=tenant_id)

    return {
        "surface_kind": "identity_continuity_diagnosis",
        "diagnosis_schema_version": IDENTITY_CONTINUITY_DIAGNOSIS_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "anchor_count": len(anchors),
        "anchor_counts_by_connector": _anchor_counts_by_connector_v1(anchors),
        "bucket_diagnosis": bucket_diagnosis,
        "anchor_samples_by_connector": _sample_anchors_by_connector_v1(anchors, raw_by_id),
        "latest_candidate_batch": latest_batch,
        "receipt_links": {
            "candidate_set_sha256": (latest_batch or {}).get("candidate_set_sha256"),
            "anchor_evidence_input_sha256": (latest_batch or {}).get("anchor_evidence_input_sha256"),
            "batch_id": (latest_batch or {}).get("batch_id"),
        },
        "repro_command": "python backend/scripts/identity_continuity_audit_snapshot.py --tenant <id> --json --diagnosis",
    }
