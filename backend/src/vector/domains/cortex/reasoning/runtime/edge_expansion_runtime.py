"""RUNTIME-03 — deterministic lawful edge expansion (explicit refs only)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.commitment_derived_causality import (
    TCRE_COMMITMENT_TRANSITION_DERIVATION_RULE_PREFIX_V1,
    TCRE_COMMITMENT_TRANSITION_KIND,
)
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    NO_COORDINATION_EDGE_SENTINEL,
    validate_tcre_edge_v1_stub,
)
from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
    REPLAY_POSTURE_REPLAY_CONFLICTED,
)
from vector.domains.cortex.reasoning.runtime.causal_edge_runtime_reducer import (
    _edge_canonical_body_v1,
    hash_tcre_causal_edge_id_v1,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)

_EXPLICIT_REF_KEYS: Final[tuple[str, ...]] = (
    "parent_issue_id",
    "linked_issue_id",
    "linked_issue_ids",
    "depends_on_issue_id",
    "commit_sha",
    "deployment_id",
    "workflow_run_id",
    "review_thread_id",
    "commitment_id",
    "continuity_owner_id",
    "same_owner_successor_id",
)


def _snapshot_refs(mat: CortexCanonicalTransformMaterialization) -> list[tuple[str, str]]:
    snap = mat.emitted_snapshot_json if isinstance(mat.emitted_snapshot_json, dict) else {}
    out: list[tuple[str, str]] = []
    for key in _EXPLICIT_REF_KEYS:
        val = snap.get(key)
        if isinstance(val, str) and val.strip():
            out.append((key, val.strip()))
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.strip():
                    out.append((key, item.strip()))
    return sorted(out, key=lambda x: (x[0], x[1]))


def _edge_from_explicit_ref(
    *,
    from_mat_id: str,
    ref_key: str,
    ref_value: str,
    kind: str,
    derivation_rule_id: str,
    causal_legality_class: str,
    tcre_policy_bundle_digest: str,
) -> dict[str, Any]:
    target = f"ref:{ref_key}:{ref_value}"
    parent_ids = sorted([f"mat:{from_mat_id}", target])
    body = {
        "tcre_causal_edge_kind": kind,
        "underlying_coordination_edge_ids": parent_ids,
        "derivation_rule_id": derivation_rule_id,
        "causal_legality_class": causal_legality_class,
        "parent_artifact_ids": parent_ids,
        "evidence_lineage": [
            {"hop_kind": "canonical_materialization", "artifact_id": from_mat_id},
            {"hop_kind": "explicit_reference", "ref_key": ref_key, "ref_value": ref_value},
        ],
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
        "source_evidence": {"ref_key": ref_key, "ref_value": ref_value},
    }
    validate_tcre_edge_v1_stub(body, max_concrete_coordination_edges=2)
    edge_id = hash_tcre_causal_edge_id_v1(body)
    return {
        "tcre_causal_edge_id": edge_id,
        "edge_body": body,
        "from_materialization_id": from_mat_id,
        "to_materialization_id": target,
    }


def reduce_commitment_edges_v1(
    materializations: Sequence[CortexCanonicalTransformMaterialization],
    *,
    tcre_policy_bundle_digest: str,
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for mat in materializations:
        snap = mat.emitted_snapshot_json if isinstance(mat.emitted_snapshot_json, dict) else {}
        cid = snap.get("commitment_id")
        if not isinstance(cid, str) or not cid.strip():
            continue
        body = {
            "tcre_causal_edge_kind": TCRE_COMMITMENT_TRANSITION_KIND,
            "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
            "derivation_rule_id": f"{TCRE_COMMITMENT_TRANSITION_DERIVATION_RULE_PREFIX_V1}runtime_v1",
            "causal_legality_class": "causal_replay_equivalent",
            "parent_artifact_ids": [f"mat:{mat.id}"],
            "evidence_lineage": [
                {"hop_kind": "canonical_materialization", "artifact_id": str(mat.id)},
                {"hop_kind": "commitment_contract", "commitment_id": cid.strip()},
            ],
            "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
        }
        validate_tcre_edge_v1_stub(body, max_concrete_coordination_edges=1)
        edges.append(
            {
                "tcre_causal_edge_id": hash_tcre_causal_edge_id_v1(body),
                "edge_body": body,
                "from_materialization_id": str(mat.id),
                "to_materialization_id": f"commitment:{cid.strip()}",
            }
        )
    return edges


def reduce_dependency_edges_v1(
    materializations: Sequence[CortexCanonicalTransformMaterialization],
    *,
    tcre_policy_bundle_digest: str,
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for mat in materializations:
        for ref_key, ref_value in _snapshot_refs(mat):
            if ref_key not in ("depends_on_issue_id", "parent_issue_id", "linked_issue_id"):
                continue
            edges.append(
                _edge_from_explicit_ref(
                    from_mat_id=str(mat.id),
                    ref_key=ref_key,
                    ref_value=ref_value,
                    kind="tcre_coordination_dependency",
                    derivation_rule_id="p06.runtime03.explicit_dependency_ref.v1",
                    causal_legality_class="causal_replay_equivalent",
                    tcre_policy_bundle_digest=tcre_policy_bundle_digest,
                )
            )
    return edges


def reduce_coordination_edges_v1(
    materializations: Sequence[CortexCanonicalTransformMaterialization],
    *,
    tcre_policy_bundle_digest: str,
) -> list[dict[str, Any]]:
    """Same workflow/review thread only — explicit ids in snapshot."""
    by_thread: dict[str, list[str]] = {}
    for mat in materializations:
        snap = mat.emitted_snapshot_json if isinstance(mat.emitted_snapshot_json, dict) else {}
        for tk in ("workflow_run_id", "review_thread_id"):
            tid = snap.get(tk)
            if isinstance(tid, str) and tid.strip():
                by_thread.setdefault(f"{tk}:{tid.strip()}", []).append(str(mat.id))
    edges: list[dict[str, Any]] = []
    for _thread, mat_ids in sorted(by_thread.items()):
        ordered = sorted(mat_ids)
        for i in range(len(ordered) - 1):
            body = _edge_canonical_body_v1(
                prev_mat_id=ordered[i],
                next_mat_id=ordered[i + 1],
                tcre_policy_bundle_digest=tcre_policy_bundle_digest,
            )
            body["tcre_causal_edge_kind"] = "tcre_coordination_thread_context"
            body["derivation_rule_id"] = "p06.runtime03.coordination_same_thread.v1"
            validate_tcre_edge_v1_stub(body, max_concrete_coordination_edges=2)
            edges.append(
                {
                    "tcre_causal_edge_id": hash_tcre_causal_edge_id_v1(body),
                    "edge_body": body,
                    "from_materialization_id": ordered[i],
                    "to_materialization_id": ordered[i + 1],
                }
            )
    return edges


def reduce_ownership_continuity_edges_v1(
    materializations: Sequence[CortexCanonicalTransformMaterialization],
    *,
    tcre_policy_bundle_digest: str,
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    by_owner: dict[str, list[str]] = {}
    for mat in materializations:
        snap = mat.emitted_snapshot_json if isinstance(mat.emitted_snapshot_json, dict) else {}
        owner = snap.get("continuity_owner_id") or snap.get("same_owner_successor_id")
        replay_posture = snap.get("replay_posture")
        if isinstance(owner, str) and owner.strip():
            by_owner.setdefault(owner.strip(), []).append(str(mat.id))
        if replay_posture == REPLAY_POSTURE_REPLAY_CONFLICTED:
            body = {
                "tcre_causal_edge_kind": "tcre_coordination_handoff",
                "underlying_coordination_edge_ids": [f"mat:{mat.id}"],
                "derivation_rule_id": "p06.runtime03.ownership_replay_conflicted.v1",
                "causal_legality_class": "causal_replay_degraded",
                "parent_artifact_ids": [f"mat:{mat.id}"],
                "evidence_lineage": [
                    {"hop_kind": "canonical_materialization", "artifact_id": str(mat.id)},
                ],
                "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
            }
            validate_tcre_edge_v1_stub(body, max_concrete_coordination_edges=1)
            edges.append(
                {
                    "tcre_causal_edge_id": hash_tcre_causal_edge_id_v1(body),
                    "edge_body": body,
                    "from_materialization_id": str(mat.id),
                    "to_materialization_id": str(mat.id),
                }
            )
    for owner, mat_ids in sorted(by_owner.items()):
        ordered = sorted(mat_ids)
        for i in range(len(ordered) - 1):
            body = {
                "tcre_causal_edge_kind": "tcre_coordination_handoff",
                "underlying_coordination_edge_ids": sorted([f"mat:{ordered[i]}", f"mat:{ordered[i+1]}"]),
                "derivation_rule_id": "p06.runtime03.ownership_same_owner.v1",
                "causal_legality_class": "causal_replay_equivalent",
                "parent_artifact_ids": [f"mat:{ordered[i]}", f"mat:{ordered[i+1]}"],
                "evidence_lineage": [
                    {"hop_kind": "canonical_materialization", "artifact_id": ordered[i]},
                    {"hop_kind": "canonical_materialization", "artifact_id": ordered[i + 1]},
                    {"hop_kind": "continuity_owner", "owner_id": owner},
                ],
                "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
            }
            validate_tcre_edge_v1_stub(body, max_concrete_coordination_edges=2)
            edges.append(
                {
                    "tcre_causal_edge_id": hash_tcre_causal_edge_id_v1(body),
                    "edge_body": body,
                    "from_materialization_id": ordered[i],
                    "to_materialization_id": ordered[i + 1],
                }
            )
    return edges


def reduce_degradation_propagation_edges_v1(
    chronology_rows: Sequence[Mapping[str, Any]],
    *,
    tcre_policy_bundle_digest: str,
) -> list[dict[str, Any]]:
    """Propagate chronology_degraded downstream along materialization order."""
    degraded_ids = [
        str(r["materialization_id"])
        for r in chronology_rows
        if r.get("chronology_legality_class") == "chronology_degraded"
    ]
    if len(degraded_ids) < 2:
        return []
    edges: list[dict[str, Any]] = []
    for i in range(len(degraded_ids) - 1):
        a, b = degraded_ids[i], degraded_ids[i + 1]
        body = {
            "tcre_causal_edge_kind": "tcre_follow_through_gap",
            "underlying_coordination_edge_ids": sorted([f"mat:{a}", f"mat:{b}"]),
            "derivation_rule_id": "p06.runtime03.chronology_degraded_propagation.v1",
            "causal_legality_class": "causal_replay_degraded",
            "parent_artifact_ids": sorted([f"mat:{a}", f"mat:{b}"]),
            "evidence_lineage": [
                {"hop_kind": "canonical_materialization", "artifact_id": a},
                {"hop_kind": "canonical_materialization", "artifact_id": b},
            ],
            "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
            "degradation_propagation": True,
        }
        validate_tcre_edge_v1_stub(body, max_concrete_coordination_edges=2)
        edges.append(
            {
                "tcre_causal_edge_id": hash_tcre_causal_edge_id_v1(body),
                "edge_body": body,
                "from_materialization_id": a,
                "to_materialization_id": b,
            }
        )
    return edges


def merge_edge_rows_deterministic_v1(*parts: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for rows in parts:
        for row in rows:
            eid = str(row["tcre_causal_edge_id"])
            by_id[eid] = row
    return [by_id[k] for k in sorted(by_id)]


def reduce_all_expanded_edges_v1(
    materializations: Sequence[CortexCanonicalTransformMaterialization],
    chronology_rows: Sequence[Mapping[str, Any]],
    *,
    tcre_policy_bundle_digest: str,
) -> list[dict[str, Any]]:
    return merge_edge_rows_deterministic_v1(
        reduce_commitment_edges_v1(materializations, tcre_policy_bundle_digest=tcre_policy_bundle_digest),
        reduce_dependency_edges_v1(materializations, tcre_policy_bundle_digest=tcre_policy_bundle_digest),
        reduce_coordination_edges_v1(materializations, tcre_policy_bundle_digest=tcre_policy_bundle_digest),
        reduce_ownership_continuity_edges_v1(
            materializations, tcre_policy_bundle_digest=tcre_policy_bundle_digest
        ),
        reduce_degradation_propagation_edges_v1(
            chronology_rows, tcre_policy_bundle_digest=tcre_policy_bundle_digest
        ),
    )
