"""Derive TCRE causal edges from ordered canonical materializations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from vector.domains.cortex.reasoning.execution_causality_constraints import (
    validate_tcre_edge_v1_stub,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)

_RUNTIME_DERIVATION_RULE_V1 = "p06.runtime01.canonical_temporal_order.v1"


def _edge_canonical_body_v1(
    *,
    prev_mat_id: str,
    next_mat_id: str,
    tcre_policy_bundle_digest: str,
) -> dict[str, Any]:
    parent_ids = sorted([f"mat:{prev_mat_id}", f"mat:{next_mat_id}"])
    return {
        "tcre_causal_edge_kind": "tcre_coordination_temporal_order",
        "underlying_coordination_edge_ids": parent_ids,
        "derivation_rule_id": _RUNTIME_DERIVATION_RULE_V1,
        "causal_legality_class": "causal_replay_equivalent",
        "parent_artifact_ids": parent_ids,
        "evidence_lineage": [
            {"hop_kind": "canonical_materialization", "artifact_id": prev_mat_id},
            {"hop_kind": "canonical_materialization", "artifact_id": next_mat_id},
        ],
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
    }


def hash_tcre_causal_edge_id_v1(edge_body: dict[str, Any]) -> str:
    payload = json.dumps(edge_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def reduce_causal_edges_v1(
    materializations: Sequence[CortexCanonicalTransformMaterialization],
    *,
    tcre_policy_bundle_digest: str,
) -> list[dict[str, Any]]:
    """One temporal-order edge per consecutive pair in canonical sort order."""
    if len(materializations) < 2:
        return []
    edges: list[dict[str, Any]] = []
    for i in range(len(materializations) - 1):
        prev_id = str(materializations[i].id)
        next_id = str(materializations[i + 1].id)
        body = _edge_canonical_body_v1(
            prev_mat_id=prev_id,
            next_mat_id=next_id,
            tcre_policy_bundle_digest=tcre_policy_bundle_digest,
        )
        validate_tcre_edge_v1_stub(body, max_concrete_coordination_edges=2)
        edge_id = hash_tcre_causal_edge_id_v1(body)
        edges.append(
            {
                "tcre_causal_edge_id": edge_id,
                "edge_body": body,
                "from_materialization_id": prev_id,
                "to_materialization_id": next_id,
            }
        )
    return edges
