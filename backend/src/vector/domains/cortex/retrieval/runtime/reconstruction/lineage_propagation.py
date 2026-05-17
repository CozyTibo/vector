"""Deterministic lineage propagation for reconstruction hits."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.lineage.artifact_lineage_graph import persist_lineage_edge_v1
from vector.domains.cortex.retrieval.retrieval_artifact_lineage import (
    build_retrieval_lineage_chain_for_query_v1,
    compute_lineage_coverage_v1,
    detect_lineage_chain_truncated_v1,
)
from vector.domains.cortex.retrieval.runtime.reconstruction.scope_planner import (
    lineage_omission_class_to_rd_v1,
)


def record_retrieval_upstream_lineage_edge_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    from_kind: str,
    from_ref: str,
    to_kind: str,
    to_ref: str,
    replay_identity: str | None = None,
) -> None:
    persist_lineage_edge_v1(
        session,
        tenant_id=tenant_id,
        from_artifact_kind=from_kind,
        from_artifact_ref=from_ref,
        to_artifact_kind=to_kind,
        to_artifact_ref=to_ref,
        edge_kind="substrate_derived",
        replay_identity=replay_identity,
    )


def attach_upstream_lineage_to_hits_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    hits: Sequence[Mapping[str, Any]],
    scope: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    omissions: list[dict[str, Any]] = []
    out: list[dict[str, Any]] = [dict(h) for h in hits]
    terminal_kind = "retrieval_index"
    terminal_ref = str(scope.get("retrieval_lookup_id") or "")
    if not terminal_ref:
        return out, omissions

    chain = build_retrieval_lineage_chain_for_query_v1(
        session,
        tenant_id=tenant_id,
        terminal_artifact_kind=terminal_kind,
        terminal_artifact_ref=terminal_ref,
        max_hops=int((envelope.get("selection_policy") or {}).get("max_lineage_hops", 32) or 32),
    )
    truncated = detect_lineage_chain_truncated_v1(chain, max_hops=64)
    coverage = compute_lineage_coverage_v1(chain, truncated=truncated, pin_match=True, edge_omissions=0)
    if truncated:
        omissions.append(
            {
                "retrieval_omission_class": "RD-LINEAGE-GAP",
                "upstream_trigger": "lineage_truncated",
            }
        )
    for hit in out:
        hit["lineage_chain"] = chain
        hit["lineage_coverage"] = coverage
    return out, omissions


def verify_lineage_continuity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    scope: Mapping[str, Any],
    omissions: list[dict[str, Any]],
) -> None:
    """Emit omission rows when upstream refs cannot be chained."""
    _ = session
    if scope.get("tcre_reconstruction_job_id") and not scope.get("causal_chain_id"):
        omissions.append(
            {
                "retrieval_omission_class": lineage_omission_class_to_rd_v1("missing_upstream_lineage"),
                "upstream_trigger": "tcre_without_chain_ref",
            }
        )
    walk = scope.get("octs_walk_id")
    if walk and not scope.get("traversal_epoch"):
        omissions.append(
            {
                "retrieval_omission_class": lineage_omission_class_to_rd_v1("traversal_lineage_gap"),
                "upstream_trigger": "walk_without_epoch",
            }
        )
    if scope.get("org_link_id") and not scope.get("org_entity_id"):
        omissions.append(
            {
                "retrieval_omission_class": lineage_omission_class_to_rd_v1("unresolved_graph_parent"),
                "upstream_trigger": "graph_ref_incomplete",
            }
        )
