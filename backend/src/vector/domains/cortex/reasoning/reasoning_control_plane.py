"""Phase 06 P06-32 — Reasoning admin **control plane** catalog (operator surfaces).

Normative: ``DOCS/cortex/reasoning/reasoning-admin-control-plane-spec.md`` §§1–3
(structural catalog + RBAC alignment; **no** tenant aggregate payloads in v1).

Exposes the mandatory **§1 Surfaces** table as a frozen, sorted-by-``surface_id`` catalog and
builders used by ``GET .../cortex/reasoning/control-plane``.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from typing import Any, Final

PHASE06_REASONING_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION: Final[int] = 1
REASONING_CONTROL_PLANE_SURFACE_VERSION_V1: Final[int] = 1
REASONING_CONTROL_PLANE_CONTRACT_V1: Final[str] = "reasoning_control_plane_catalog_v1"

REASONING_ADMIN_CONTROL_PLANE_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/reasoning/reasoning-admin-control-plane-spec.md"
)
REASONING_DANGEROUS_ACTION_SAFETY_MODEL_REF_V1: Final[str] = (
    "DOCS/cortex/10-admin/dangerous-action-safety-model.md"
)

REASONING_CONTROL_PLANE_RBAC_SUBSTRATE_LITERAL_V1: Final[str] = (
    "Reasoning admin surfaces are substrate evidence operators — not end-user intelligence UI."
)

REASONING_CONTROL_PLANE_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/reasoning/control-plane",
)


@dataclass(frozen=True, slots=True)
class ReasoningControlPlaneSurfaceV1:
    surface_id: str
    title: str
    operator_purpose: str


_REASONING_CONTROL_PLANE_SURFACES_RAW_V1: Final[tuple[ReasoningControlPlaneSurfaceV1, ...]] = (
    ReasoningControlPlaneSurfaceV1(
        surface_id="ambiguity_propagation_inspector",
        title="Ambiguity propagation inspector",
        operator_purpose=(
            "Canonical AMB-* ids plus blocked derivations backed by the ambiguity registry."
        ),
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="causal_chain_debugger",
        title="Causal chain debugger",
        operator_purpose=(
            "TCRECausalEdge_v1 list / DAG with tcre_causal_edge_kind, "
            "underlying_coordination_edge_ids, hop-level lineage to raw."
        ),
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="causal_contradiction_topology",
        title="Causal contradiction topology",
        operator_purpose="Partition graph from temporal / causal conflict doctrine.",
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="chronology_debugger",
        title="Chronology debugger",
        operator_purpose=(
            "Windows, half-open intervals, silence causality rule id sources where applicable."
        ),
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="continuity_breakpoints",
        title="Continuity breakpoints",
        operator_purpose="Cross-system bridge failures plus rank(S) ladder display.",
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="degradation_topology",
        title="Degradation topology",
        operator_purpose="CD-* severity rollup by tenant and time window.",
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="policy_bundle_inspector",
        title="Policy bundle inspector",
        operator_purpose=(
            "Active tcre_policy_pack_id, tcre_policy_bundle_digest, caps "
            "(max_causal_hops_*, transitive limits, breakpoint priorities)."
        ),
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="reasoning_health_strip",
        title="Reasoning health strip",
        operator_purpose=(
            "replay_safe_ordering, chronology_legality_class, replay_posture, "
            "causal_legality_class, sorted CD-* rollup — no collapsed single green."
        ),
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="receipts_explorer",
        title="Receipts explorer",
        operator_purpose="Reasoning receipts plus proof artifacts (hashes).",
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="replay_pressure",
        title="Replay pressure",
        operator_purpose="Queue depth, job latency, equivalence failures count.",
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="replay_reasoning_debugger",
        title="Replay reasoning debugger",
        operator_purpose=(
            "Inputs: walk hashes, index epoch, reasoning_replay_permutation_v1 JSON, "
            "policy digest → diff of receipt digests (structural diff P1 until specified)."
        ),
    ),
    ReasoningControlPlaneSurfaceV1(
        surface_id="temporal_legality_inspector",
        title="Temporal legality inspector",
        operator_purpose=(
            "Anchors, chains, skew flags, export order plus projection receipt linkage."
        ),
    ),
)

REASONING_CONTROL_PLANE_SURFACES_V1: Final[tuple[ReasoningControlPlaneSurfaceV1, ...]] = tuple(
    sorted(_REASONING_CONTROL_PLANE_SURFACES_RAW_V1, key=lambda s: s.surface_id)
)


def list_reasoning_control_plane_surface_ids_v1() -> tuple[str, ...]:
    return tuple(s.surface_id for s in REASONING_CONTROL_PLANE_SURFACES_V1)


def build_reasoning_control_plane_catalog_v1(
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    """Return the **reasoning_control_plane_catalog_v1** document (static surfaces + pointers)."""
    if tenant_id is None:
        tid = ""
    else:
        tid = str(tenant_id)
    return {
        "tenant_id": tid,
        "reasoning_control_plane_runtime_schema_version": (
            PHASE06_REASONING_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION
        ),
        "reasoning_control_plane_surface_version": REASONING_CONTROL_PLANE_SURFACE_VERSION_V1,
        "reasoning_control_plane_contract": REASONING_CONTROL_PLANE_CONTRACT_V1,
        "surfaces": [asdict(s) for s in REASONING_CONTROL_PLANE_SURFACES_V1],
        "doctrine_anchors": [REASONING_ADMIN_CONTROL_PLANE_SPEC_REF_V1],
        "dangerous_action_doctrine_ref": REASONING_DANGEROUS_ACTION_SAFETY_MODEL_REF_V1,
        "rbac_substrate_alignment_literal": REASONING_CONTROL_PLANE_RBAC_SUBSTRATE_LITERAL_V1,
    }


def _rcp_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": "reasoning-control-plane-meta-v1",
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase06_reasoning_control_plane_runtime_schema_version": (
                PHASE06_REASONING_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp06_rcp01_surface_catalog_sorted_unique_static() -> dict[str, Any]:
    errors: list[str] = []
    ids = [s.surface_id for s in REASONING_CONTROL_PLANE_SURFACES_V1]
    if len(ids) != 12:
        errors.append(f"surface_count_expected_12_got_{len(ids)}")
    if ids != sorted(ids):
        errors.append("surface_ids_not_sorted")
    if len(set(ids)) != len(ids):
        errors.append("duplicate_surface_id")
    return _rcp_meta("gp06_rcp01_surface_catalog_sorted_unique", errors)


def verify_gp06_rcp02_surfaces_match_admin_spec_table_static() -> dict[str, Any]:
    """Titles align with ``reasoning-admin-control-plane-spec.md`` §1 (stable slug → title)."""
    errors: list[str] = []
    want_titles = {
        "ambiguity_propagation_inspector": "Ambiguity propagation inspector",
        "causal_chain_debugger": "Causal chain debugger",
        "causal_contradiction_topology": "Causal contradiction topology",
        "chronology_debugger": "Chronology debugger",
        "continuity_breakpoints": "Continuity breakpoints",
        "degradation_topology": "Degradation topology",
        "policy_bundle_inspector": "Policy bundle inspector",
        "reasoning_health_strip": "Reasoning health strip",
        "receipts_explorer": "Receipts explorer",
        "replay_pressure": "Replay pressure",
        "replay_reasoning_debugger": "Replay reasoning debugger",
        "temporal_legality_inspector": "Temporal legality inspector",
    }
    for s in REASONING_CONTROL_PLANE_SURFACES_V1:
        if want_titles.get(s.surface_id) != s.title:
            errors.append(f"title_mismatch:{s.surface_id}")
        if not s.operator_purpose.strip():
            errors.append(f"empty_operator_purpose:{s.surface_id}")
    if set(want_titles.keys()) != set(list_reasoning_control_plane_surface_ids_v1()):
        errors.append("surface_id_set_mismatch_spec")
    return _rcp_meta("gp06_rcp02_surfaces_match_admin_spec_table", errors)


def verify_gp06_rcp03_doctrine_refs_frozen_static() -> dict[str, Any]:
    errors: list[str] = []
    if "reasoning-admin-control-plane-spec" not in REASONING_ADMIN_CONTROL_PLANE_SPEC_REF_V1:
        errors.append("admin_spec_ref_drift")
    if "10-admin" not in REASONING_DANGEROUS_ACTION_SAFETY_MODEL_REF_V1:
        errors.append("dangerous_action_ref_drift")
    return _rcp_meta("gp06_rcp03_doctrine_refs_frozen", errors)


def verify_gp06_rcp04_build_catalog_contract_shape_static() -> dict[str, Any]:
    errors: list[str] = []
    doc = build_reasoning_control_plane_catalog_v1(tenant_id=uuid.UUID(int=0))
    if doc.get("reasoning_control_plane_contract") != REASONING_CONTROL_PLANE_CONTRACT_V1:
        errors.append("contract_literal_mismatch")
    got_sv = doc.get("reasoning_control_plane_surface_version")
    if got_sv != REASONING_CONTROL_PLANE_SURFACE_VERSION_V1:
        errors.append("surface_version_mismatch")
    if len(doc.get("surfaces", [])) != 12:
        errors.append("catalog_surfaces_len")
    if doc.get("tenant_id") != str(uuid.UUID(int=0)):
        errors.append("tenant_id_echo_mismatch")
    return _rcp_meta("gp06_rcp04_build_catalog_contract_shape", errors)


def verify_gp06_rcp05_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    if REASONING_CONTROL_PLANE_ADMIN_OPENAPI_PATHS_V1 != (
        "/admin/tenants/{tenant_id}/cortex/reasoning/control-plane",
    ):
        errors.append("admin_path_tuple_drift")
    for p in REASONING_CONTROL_PLANE_ADMIN_OPENAPI_PATHS_V1:
        if "cortex/reasoning/control-plane" not in p:
            errors.append(f"path_missing_reasoning_segment:{p}")
    return _rcp_meta("gp06_rcp05_admin_openapi_path_matrix", errors)


def verify_gp06_rcp06_rbac_substrate_literal_frozen_static() -> dict[str, Any]:
    errors: list[str] = []
    lit = REASONING_CONTROL_PLANE_RBAC_SUBSTRATE_LITERAL_V1.lower()
    if "substrate" not in lit:
        errors.append("rbac_literal_missing_substrate")
    return _rcp_meta("gp06_rcp06_rbac_substrate_literal_frozen", errors)
