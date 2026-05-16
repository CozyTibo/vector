"""Phase 06 P06-33 — Reasoning **runtime legality matrix** (**R‑LEG‑01..05**).

Normative: ``DOCS/cortex/reasoning/reasoning-runtime-legality-matrix.md`` (production gates,
forbidden deployments, waiver discipline mirror).

Static catalog + CI‑wired checks where predicates already have shipped oracles (e.g. **R‑LEG‑02**
↔ **G‑P06‑ANTI‑01**).
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from typing import Any, Final

from vector.domains.cortex.reasoning.anti_goals import verify_gp06_anti01_reasoning_package_static

PHASE06_REASONING_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION: Final[int] = 1
REASONING_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1: Final[str] = (
    "reasoning_runtime_legality_matrix_catalog_v1"
)
REASONING_RUNTIME_LEGALITY_MATRIX_SURFACE_VERSION_V1: Final[int] = 1

REASONING_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/reasoning/reasoning-runtime-legality-matrix.md"
)
PHASE05_RUNTIME_LEGALITY_MATRIX_REF_V1: Final[str] = (
    "DOCS/cortex/05-traversal/phase-05-runtime-legality-matrix.md"
)
CHRONOLOGY_REPLAY_LEGALITY_STATE_MACHINE_REF_V1: Final[str] = (
    "DOCS/cortex/reasoning/chronology-replay-legality-state-machine.md"
)
REASONING_RUNTIME_LEGALITY_DANGEROUS_ACTION_REF_V1: Final[str] = (
    "DOCS/cortex/10-admin/dangerous-action-safety-model.md"
)
REASONING_VERIFICATION_WAIVERS_YAML_FUTURE_PATH_V1: Final[str] = (
    "DOCS/cortex/reasoning/waivers/reasoning_verification_waivers.yaml"
)

REASONING_RUNTIME_LEGALITY_MATRIX_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/reasoning/runtime-legality-matrix",
)


@dataclass(frozen=True, slots=True)
class ReasoningRuntimeLegalityPredicateV1:
    predicate_id: str
    required_evidence: str


_PredTuple = tuple[ReasoningRuntimeLegalityPredicateV1, ...]

_REASONING_RUNTIME_LEGALITY_PREDICATES_RAW_V1: Final[_PredTuple] = (
    ReasoningRuntimeLegalityPredicateV1(
        predicate_id="R-LEG-01",
        required_evidence=(
            "Phase 05 phase-05-runtime-legality-matrix.md production predicates satisfied "
            "for any walk-ingesting reducer path (cite predicate ids in deployment checklist)."
        ),
    ),
    ReasoningRuntimeLegalityPredicateV1(
        predicate_id="R-LEG-02",
        required_evidence="Phase 06 G-P06-ANTI-01 green in CI (package import / cognition scan).",
    ),
    ReasoningRuntimeLegalityPredicateV1(
        predicate_id="R-LEG-03",
        required_evidence=(
            "chronology_legality_class not in {chronology_unresolved} for strict causal mode "
            "or max_causal_hops_degraded lane with operator banner; never infer from "
            "replay_safe_ordering string alone (chronology-replay-legality-state-machine.md)."
        ),
    ),
    ReasoningRuntimeLegalityPredicateV1(
        predicate_id="R-LEG-04",
        required_evidence=(
            "Redis / queue isolation for reasoning jobs documented — no cross-tenant lease bleed."
        ),
    ),
    ReasoningRuntimeLegalityPredicateV1(
        predicate_id="R-LEG-05",
        required_evidence=(
            "Operator dangerous actions behind confirmation phrase + audit log "
            "(dangerous-action-safety-model.md)."
        ),
    ),
)

REASONING_RUNTIME_LEGALITY_PREDICATES_V1: Final[_PredTuple] = tuple(
    sorted(_REASONING_RUNTIME_LEGALITY_PREDICATES_RAW_V1, key=lambda p: p.predicate_id)
)


@dataclass(frozen=True, slots=True)
class ReasoningRuntimeForbiddenDeploymentV1:
    forbidden_id: str
    description: str


_ForbTuple = tuple[ReasoningRuntimeForbiddenDeploymentV1, ...]

REASONING_RUNTIME_FORBIDDEN_DEPLOYMENTS_V1: Final[_ForbTuple] = (
    ReasoningRuntimeForbiddenDeploymentV1(
        forbidden_id="R-FD-01",
        description="Reasoning workers without Phase 05 ingress validation when consuming walks.",
    ),
    ReasoningRuntimeForbiddenDeploymentV1(
        forbidden_id="R-FD-02",
        description=(
            "Multi-tenant shared mutable cache for causal graphs without tenant key partition."
        ),
    ),
)


def list_reasoning_runtime_legality_predicate_ids_v1() -> tuple[str, ...]:
    return tuple(p.predicate_id for p in REASONING_RUNTIME_LEGALITY_PREDICATES_V1)


def build_reasoning_runtime_legality_matrix_catalog_v1(
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    tid = "" if tenant_id is None else str(tenant_id)
    return {
        "tenant_id": tid,
        "reasoning_runtime_legality_matrix_runtime_schema_version": (
            PHASE06_REASONING_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION
        ),
        "reasoning_runtime_legality_matrix_surface_version": (
            REASONING_RUNTIME_LEGALITY_MATRIX_SURFACE_VERSION_V1
        ),
        "reasoning_runtime_legality_matrix_contract": REASONING_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1,
        "predicates": [asdict(p) for p in REASONING_RUNTIME_LEGALITY_PREDICATES_V1],
        "forbidden_deployments": [asdict(f) for f in REASONING_RUNTIME_FORBIDDEN_DEPLOYMENTS_V1],
        "doctrine_anchors": [
            REASONING_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1,
            PHASE05_RUNTIME_LEGALITY_MATRIX_REF_V1,
            CHRONOLOGY_REPLAY_LEGALITY_STATE_MACHINE_REF_V1,
            REASONING_RUNTIME_LEGALITY_DANGEROUS_ACTION_REF_V1,
        ],
        "waiver_yaml_future_path": REASONING_VERIFICATION_WAIVERS_YAML_FUTURE_PATH_V1,
    }


def _rlm_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": "reasoning-runtime-legality-matrix-meta-v1",
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase06_reasoning_runtime_legality_matrix_runtime_schema_version": (
                PHASE06_REASONING_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp06_rlm01_predicate_catalog_five_sorted_unique_static() -> dict[str, Any]:
    errors: list[str] = []
    ids = list_reasoning_runtime_legality_predicate_ids_v1()
    want = ("R-LEG-01", "R-LEG-02", "R-LEG-03", "R-LEG-04", "R-LEG-05")
    if ids != want:
        errors.append(f"predicate_id_tuple_mismatch:{ids!r}")
    if len(set(ids)) != len(ids):
        errors.append("duplicate_predicate_id")
    return _rlm_meta("gp06_rlm01_predicate_catalog_five_sorted_unique", errors)


def verify_gp06_rlm02_r_leg02_anti01_ci_green_static() -> dict[str, Any]:
    """**R‑LEG‑02** — **G‑P06‑ANTI‑01** static oracle passes (CI substrate)."""
    out = verify_gp06_anti01_reasoning_package_static()
    passed = bool(out.get("passed"))
    return {
        "id": "P06-33-rlm-r-leg-02",
        "name": "gp06_rlm02_r_leg02_anti01_ci_green",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "underlying": out,
            "phase06_reasoning_runtime_legality_matrix_runtime_schema_version": (
                PHASE06_REASONING_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp06_rlm03_cross_doc_anchors_frozen_static() -> dict[str, Any]:
    errors: list[str] = []
    if "reasoning-runtime-legality-matrix" not in REASONING_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1:
        errors.append("matrix_spec_ref_drift")
    if "05-traversal" not in PHASE05_RUNTIME_LEGALITY_MATRIX_REF_V1:
        errors.append("phase05_matrix_ref_drift")
    chrono_ref = CHRONOLOGY_REPLAY_LEGALITY_STATE_MACHINE_REF_V1
    if "chronology-replay-legality-state-machine" not in chrono_ref:
        errors.append("chronology_sm_ref_drift")
    if "10-admin" not in REASONING_RUNTIME_LEGALITY_DANGEROUS_ACTION_REF_V1:
        errors.append("dangerous_action_ref_drift")
    return _rlm_meta("gp06_rlm03_cross_doc_anchors_frozen", errors)


def verify_gp06_rlm04_forbidden_deployments_shape_static() -> dict[str, Any]:
    errors: list[str] = []
    rows = REASONING_RUNTIME_FORBIDDEN_DEPLOYMENTS_V1
    if len(rows) != 2:
        errors.append("forbidden_row_count")
    ids = [r.forbidden_id for r in rows]
    if ids != sorted(ids):
        errors.append("forbidden_ids_not_sorted")
    for r in rows:
        if not r.description.strip():
            errors.append(f"empty_forbidden_description:{r.forbidden_id}")
    return _rlm_meta("gp06_rlm04_forbidden_deployments_shape", errors)


def verify_gp06_rlm05_waiver_yaml_future_path_literal_static() -> dict[str, Any]:
    errors: list[str] = []
    p = REASONING_VERIFICATION_WAIVERS_YAML_FUTURE_PATH_V1
    if "waivers/reasoning_verification_waivers.yaml" not in p:
        errors.append("waiver_path_drift")
    return _rlm_meta("gp06_rlm05_waiver_yaml_future_path_literal", errors)


def verify_gp06_rlm06_build_catalog_contract_shape_static() -> dict[str, Any]:
    errors: list[str] = []
    doc = build_reasoning_runtime_legality_matrix_catalog_v1(tenant_id=uuid.UUID(int=0))
    want_contract = REASONING_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1
    if doc.get("reasoning_runtime_legality_matrix_contract") != want_contract:
        errors.append("contract_literal_mismatch")
    if len(doc.get("predicates", [])) != 5:
        errors.append("predicates_len")
    if len(doc.get("forbidden_deployments", [])) != 2:
        errors.append("forbidden_len")
    if doc.get("tenant_id") != str(uuid.UUID(int=0)):
        errors.append("tenant_id_echo_mismatch")
    return _rlm_meta("gp06_rlm06_build_catalog_contract_shape", errors)


def verify_gp06_rlm07_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = ("/admin/tenants/{tenant_id}/cortex/reasoning/runtime-legality-matrix",)
    if REASONING_RUNTIME_LEGALITY_MATRIX_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    for p in REASONING_RUNTIME_LEGALITY_MATRIX_ADMIN_OPENAPI_PATHS_V1:
        if "cortex/reasoning/runtime-legality-matrix" not in p:
            errors.append(f"path_missing_matrix_segment:{p}")
    return _rlm_meta("gp06_rlm07_admin_openapi_path_matrix", errors)
