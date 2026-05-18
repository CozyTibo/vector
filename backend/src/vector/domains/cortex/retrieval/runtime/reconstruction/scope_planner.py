"""Deterministic reconstruction scope planner — lawful ref resolution only."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy.orm import Session

PHASE07_RECONSTRUCTION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RECONSTRUCTION_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
    {
        "causal_chain",
        "execution_continuity",
        "chronology_window",
        "ownership_continuity",
        "dependency_propagation",
        "degradation_survey",
        "lineage_explorer",
        "traversal_lineage",
        "materialization_as_of",
    }
)

LINEAGE_OMISSION_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "missing_upstream_lineage",
        "unresolved_graph_parent",
        "traversal_lineage_gap",
        "replay_lineage_mismatch",
    }
)

LINEAGE_OMISSION_CLASS_TO_RD_V1: Final[dict[str, str]] = {
    "missing_upstream_lineage": "RD-LINEAGE-GAP",
    "unresolved_graph_parent": "RD-GRAPH-ORPHAN",
    "traversal_lineage_gap": "RD-TRAVERSAL-IDLE",
    "replay_lineage_mismatch": "RD-REPLAY-UNSAFE",
}


def lineage_omission_class_to_rd_v1(omission_class: str) -> str:
    return LINEAGE_OMISSION_CLASS_TO_RD_V1.get(str(omission_class).strip(), str(omission_class))


def build_reconstruction_catalog_v1() -> dict[str, Any]:
    return {
        "reconstruction_runtime_schema_version": PHASE07_RECONSTRUCTION_RUNTIME_SCHEMA_VERSION,
        "reconstruction_workloads": sorted(RECONSTRUCTION_WORKLOADS_V1),
        "lineage_omission_classes": sorted(LINEAGE_OMISSION_CLASSES_V1),
        "surface_kind": "runtime_backed",
    }


def workload_uses_reconstruction_v1(workload_class: str) -> bool:
    return str(workload_class).strip() in RECONSTRUCTION_WORKLOADS_V1


def plan_reconstruction_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    row: Any,
    retrieval_lookup_id: str,
) -> dict[str, Any]:
    """Resolve deterministic artifact refs for reconstruction (no inference)."""
    _ = session
    ref = dict(getattr(row, "artifact_ref_json", None) or {})
    _raw_pins = envelope.get("replay_pins")
    pins: dict[str, Any] = _raw_pins if isinstance(_raw_pins, dict) else {}
    _raw_addressing = envelope.get("addressing")
    addressing: dict[str, Any] = _raw_addressing if isinstance(_raw_addressing, dict) else {}

    scope: dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "retrieval_lookup_id": str(retrieval_lookup_id),
        "index_kind": getattr(row, "index_kind", None),
        "index_key": getattr(row, "index_key", None),
        "index_epoch": getattr(row, "index_epoch", None) or pins.get("index_epoch"),
        "traversal_epoch": getattr(row, "traversal_epoch", None),
        "replay_identity": getattr(row, "replay_identity", None),
        "causal_chain_id": ref.get("causal_chain_id"),
        "tcre_reconstruction_job_id": ref.get("tcre_reconstruction_job_id"),
        "octs_walk_id": ref.get("octs_walk_id") or ref.get("walk_id"),
        "org_link_id": ref.get("org_link_id"),
        "org_entity_id": ref.get("org_entity_id"),
        "materialization_id": ref.get("materialization_id")
        or (addressing.get("materialization_id") if addressing else None),
        "chronology_window_ref": addressing.get("chronology_window_ref") if addressing else None,
        "retrieval_chain_ref": addressing.get("retrieval_chain_ref") if addressing else None,
        "retrieval_walk_ref": addressing.get("retrieval_walk_ref") if addressing else None,
    }
    missing: list[str] = []
    if not scope.get("causal_chain_id") and not scope.get("octs_walk_id") and not scope.get("org_link_id"):
        missing.append("missing_upstream_lineage")
    scope["lineage_gaps"] = missing
    return scope
