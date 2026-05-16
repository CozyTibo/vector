"""RUNTIME-02 — deterministic causal edge explanation projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

TCRE_OPERATOR_EDGE_EXPLANATION_SCHEMA_VERSION: Final[int] = 1

_EDGE_RULE_LABELS: Final[dict[str, str]] = {
    "p06.runtime01.canonical_temporal_order.v1": "TCRE-EDGE-TEMPORAL-01",
}


def edge_derivation_rule_label_v1(derivation_rule_id: str) -> str:
    return _EDGE_RULE_LABELS.get(derivation_rule_id, derivation_rule_id)


def build_edge_explanation_summary_v1(
    *,
    derivation_rule_id: str,
    edge_kind: str,
    causal_legality_class: str,
    from_materialization_id: str,
    to_materialization_id: str,
) -> str:
    label = edge_derivation_rule_label_v1(derivation_rule_id)
    return (
        f"Temporal successor edge ({edge_kind}) from ordered canonical materializations "
        f"{from_materialization_id} → {to_materialization_id} under {label}; "
        f"causal_legality_class={causal_legality_class}."
    )


def project_causal_edge_explanation_v1(
    *,
    edge_row: Mapping[str, Any],
    from_kind: str | None,
    to_kind: str | None,
    from_chronology_class: str | None,
    to_chronology_class: str | None,
    tcre_policy_bundle_digest: str,
    replay_posture: str,
) -> dict[str, Any]:
    body_edge = dict(edge_row.get("edge_body") or {})
    edge_id = str(edge_row.get("tcre_causal_edge_id") or "")
    from_id = str(edge_row.get("from_materialization_id") or "")
    to_id = str(edge_row.get("to_materialization_id") or "")
    kind = str(body_edge.get("tcre_causal_edge_kind") or "")
    deriv = str(body_edge.get("derivation_rule_id") or "")
    legality = str(body_edge.get("causal_legality_class") or "")
    summary = build_edge_explanation_summary_v1(
        derivation_rule_id=deriv,
        edge_kind=kind,
        causal_legality_class=legality,
        from_materialization_id=from_id,
        to_materialization_id=to_id,
    )
    source_evidence = body_edge.get("source_evidence")
    core = {
        "schema_version": TCRE_OPERATOR_EDGE_EXPLANATION_SCHEMA_VERSION,
        "tcre_causal_edge_id": edge_id,
        "source_evidence": dict(source_evidence) if isinstance(source_evidence, dict) else None,
        "degradation_propagation": bool(body_edge.get("degradation_propagation")),
        "from_materialization_id": from_id,
        "to_materialization_id": to_id,
        "canonical_object_kind_from": from_kind,
        "canonical_object_kind_to": to_kind,
        "tcre_causal_edge_kind": kind,
        "derivation_rule_id": deriv,
        "derivation_rule_label": edge_derivation_rule_label_v1(deriv),
        "causal_legality_class": legality,
        "continuity_source": "canonical_materialization_order",
        "replay_posture": replay_posture,
        "from_chronology_legality_class": from_chronology_class,
        "to_chronology_legality_class": to_chronology_class,
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
        "retrieval_lookup_id": f"edge:{edge_id}",
        "parent_artifact_ids": list(body_edge.get("parent_artifact_ids") or []),
    }
    digest = hash_reasoning_canonical_json_sha256_v1(core)
    return {**core, "explanation_summary": summary, "explanation_digest": digest, "edge_body": body_edge}
