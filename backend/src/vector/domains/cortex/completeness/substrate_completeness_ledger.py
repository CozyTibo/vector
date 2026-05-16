"""Global substrate completeness ledger (single tenant health view)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.completeness._completeness_common import (
    SUBSTRATE_COMPLETENESS_LEDGER_SCHEMA_VERSION,
    derive_global_replay_posture,
    derive_substrate_state_from_stages,
)
from vector.domains.cortex.completeness.canonical_completeness_projection import (
    project_canonical_completeness_v1,
)
from vector.domains.cortex.completeness.completeness_degradation_projection import (
    build_completeness_degradation_envelope_v1,
)
from vector.domains.cortex.completeness.graph_completeness_projection import (
    project_graph_completeness_v1,
)
from vector.domains.cortex.completeness.identity_completeness_projection import (
    project_identity_completeness_v1,
)
from vector.domains.cortex.completeness.ingestion_completeness_projection import (
    project_ingestion_completeness_v1,
)
from vector.domains.cortex.completeness.tcre_completeness_projection import (
    project_tcre_completeness_v1,
)
from vector.domains.cortex.completeness.traversal_completeness_projection import (
    project_traversal_completeness_v1,
)
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)


def build_substrate_completeness_ledger_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    stages = [
        project_ingestion_completeness_v1(session, tenant_id=tenant_id),
        project_canonical_completeness_v1(session, tenant_id=tenant_id),
        project_identity_completeness_v1(session, tenant_id=tenant_id),
        project_graph_completeness_v1(session, tenant_id=tenant_id),
        project_traversal_completeness_v1(session, tenant_id=tenant_id),
        project_tcre_completeness_v1(session, tenant_id=tenant_id),
    ]
    propagation = build_completeness_degradation_envelope_v1(stages)
    substrate_state = derive_substrate_state_from_stages(stages)
    replay_posture = derive_global_replay_posture(stages)

    aggregate = {
        "raw_exhaust": {
            "total_raw_events": stages[0]["metrics"].get("raw_event_total", 0),
            "missing_raw_windows": stages[0]["omission_classes"].get("ingestion_window_missing", 0),
            "duplicate_rate_percent": stages[0]["metrics"].get("ingestion_coverage_percent", 0),
        },
        "canonical": {
            "canonicalized_percent": stages[1]["metrics"].get("conversion_percent", 0),
            "unsupported_percent": stages[1]["metrics"].get("unsupported_count", 0),
            "parse_failure_percent": stages[1]["metrics"].get("parse_failed_count", 0),
        },
        "identity": {
            "resolved_percent": stages[2]["metrics"].get("resolved_identity_percent", 0),
            "unresolved_percent": stages[2]["unresolved_percent"],
            "replay_conflicts_percent": stages[2]["metrics"].get("replay_drift_total", 0),
        },
        "graph": {
            "connected_percent": stages[3]["metrics"].get("graph_connectivity_percent", 0),
            "orphan_percent": stages[3]["unresolved_percent"],
            "degraded_continuity_percent": stages[3]["degraded_percent"],
        },
        "traversal": {
            "replay_covered_percent": stages[4]["metrics"].get("traversal_replay_coverage_percent", 0),
            "frontier_gaps_percent": stages[4]["omitted_count"],
            "stale_traversal_warnings": len(stages[4]["drift_warnings"]),
        },
        "tcre": {
            "strict_chronology_percent": stages[5]["metrics"].get("strict_chronology_percent", 0),
            "degraded_chronology_percent": stages[5]["metrics"].get("degraded_chronology_percent", 0),
            "omitted_edges_percent": stages[5]["omitted_count"],
            "replay_divergence_percent": stages[5]["metrics"].get("replay_divergence_rate", 0),
        },
    }

    body = {
        "substrate_completeness_ledger_schema_version": SUBSTRATE_COMPLETENESS_LEDGER_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "substrate_state": substrate_state,
        "substrate_replay_posture": replay_posture,
        "pipeline_stages": stages,
        "degradation_propagation": propagation,
        "aggregate": aggregate,
    }
    body["ledger_digest"] = hash_reasoning_canonical_json_sha256_v1(
        {
            "tenant_id": body["tenant_id"],
            "substrate_state": substrate_state,
            "substrate_replay_posture": replay_posture,
            "stage_digests": [s.get("stage_receipt_digest") for s in stages],
            "propagation_digest": propagation.get("envelope_digest"),
        }
    )
    return body
