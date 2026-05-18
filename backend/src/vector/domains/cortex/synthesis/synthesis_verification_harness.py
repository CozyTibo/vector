"""Phase 08 P08-26 — **G-P08-*** verification harness (catalog + wired static runners).

Normative: ``DOCS/cortex/synthesis/phase-08-testing-strategy.md`` (gate table + CI staging).

Owns gate id → **STAGE** row + static ``runner`` map; ``run_synthesis_gp08_pr_blocking_static_stages_v1``
(stages **A+B+C**) and ``run_synthesis_gp08_wired_verification_stages_v1`` for full CI slices.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal

PHASE08_SYNTHESIS_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_VERIFICATION_HARNESS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-testing-strategy.md"
)

SYNTHESIS_VERIFICATION_HARNESS_CATALOG_VERSION_V1: Final[int] = 1

SYNTHESIS_VERIFICATION_MODE_ENV: Final[str] = "SYNTHESIS_VERIFICATION_MODE"

from vector.domains.cortex.synthesis.synthesis_certification_pack import (
    SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
    SYNTHESIS_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    verify_gp08_close01_synthesis_cert_pack_closure_static,
    verify_gp08_close01_synthesis_cert_pack_shape_reference_static,
)

SYNTHESIS_VERIFICATION_HARNESS_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/catalog/cortex/synthesis/verification-harness",
)

SynthesisGateStageV1 = Literal[
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
]
SynthesisGateSeverityV1 = Literal["hard_fail", "warn"]

SYNTHESIS_GP08_DOCTRINE_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P08-ANTI-01",
    "G-P08-ANTI-02",
    "G-P08-CITE-01",
    "G-P08-CLOSE-01",
    "G-P08-CP-01",
    "G-P08-DEG-01",
    "G-P08-DEG-02",
    "G-P08-ECO-01",
    "G-P08-FSM-01",
    "G-P08-INGRESS-01",
    "G-P08-LEG-01",
    "G-P08-LLM-01",
    "G-P08-PRM-01",
    "G-P08-REPLAY-01",
    "G-P08-REPLAY-02",
    "G-P08-RLM-01",
    "G-P08-SCHEMA-01",
    "G-P08-TVER-01",
    "G-P08-WF-01",
)

SYNTHESIS_GP08_CORRUPTION_BUNDLES_V1: Final[dict[str, frozenset[str]]] = {
    "replay_surface": frozenset({"G-P08-REPLAY-01", "G-P08-REPLAY-02"}),
    "ingress_anti_surface": frozenset({"G-P08-ANTI-01", "G-P08-ANTI-02", "G-P08-SCHEMA-01"}),
    "control_plane_surface": frozenset({"G-P08-CP-01", "G-P08-TVER-01", "G-P08-WF-01"}),
}

_WARN_SYNTHESIS_GATES_V1: Final[frozenset[str]] = frozenset()

_SYNTHESIS_GATE_STAGE_V1: Final[dict[str, SynthesisGateStageV1]] = {
    "G-P08-ANTI-01": "A",
    "G-P08-ANTI-02": "A",
    "G-P08-SCHEMA-01": "A",
    "G-P08-INGRESS-01": "B",
    "G-P08-LEG-01": "B",
    "G-P08-CITE-01": "B",
    "G-P08-FSM-01": "B",
    "G-P08-LLM-01": "B",
    "G-P08-PRM-01": "B",
    "G-P08-DEG-01": "B",
    "G-P08-DEG-02": "B",
    "G-P08-REPLAY-01": "C",
    "G-P08-REPLAY-02": "C",
    "G-P08-CP-01": "D",
    "G-P08-TVER-01": "D",
    "G-P08-WF-01": "D",
    "G-P08-ECO-01": "E",
    "G-P08-RLM-01": "E",
    "G-P08-CLOSE-01": "Z",
}

SYNTHESIS_GP08_STAGE_A_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P08-ANTI-01",
    "G-P08-ANTI-02",
    "G-P08-SCHEMA-01",
)

SYNTHESIS_GP08_STAGE_B_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P08-INGRESS-01",
    "G-P08-LEG-01",
    "G-P08-CITE-01",
    "G-P08-FSM-01",
    "G-P08-LLM-01",
    "G-P08-PRM-01",
    "G-P08-DEG-01",
    "G-P08-DEG-02",
)

SYNTHESIS_GP08_STAGE_C_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P08-REPLAY-01",
    "G-P08-REPLAY-02",
)

SYNTHESIS_GP08_STAGE_D_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P08-CP-01",
    "G-P08-TVER-01",
    "G-P08-WF-01",
)

SYNTHESIS_GP08_STAGE_E_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P08-ECO-01",
    "G-P08-RLM-01",
)

_HARNESS_RUN_LEDGER_MAX_V1: Final[int] = 32
_harness_run_ledger_v1: list[dict[str, Any]] = []


def default_severity_for_synthesis_gate_v1(gate_id: str) -> SynthesisGateSeverityV1:
    return "warn" if gate_id in _WARN_SYNTHESIS_GATES_V1 else "hard_fail"


def synthesis_gp08_gate_stage_v1(gate_id: str) -> SynthesisGateStageV1 | None:
    return _SYNTHESIS_GATE_STAGE_V1.get(gate_id)


def list_synthesis_gp08_doctrine_gate_ids_v1() -> tuple[str, ...]:
    return SYNTHESIS_GP08_DOCTRINE_GATE_IDS_V1


def _meta_result(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": "synthesis-gp08-harness-meta-v1",
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase08_synthesis_verification_harness_runtime_schema_version": (
                PHASE08_SYNTHESIS_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def _compose_gate_results_v1(
    gate_id: str,
    name: str,
    parts: list[dict[str, Any]],
) -> dict[str, Any]:
    ok = all(bool(p.get("passed")) for p in parts)
    return {
        "id": gate_id,
        "name": name,
        "passed": ok,
        "severity": default_severity_for_synthesis_gate_v1(gate_id),
        "detail": {
            "sub_results": parts,
            "synthesis_verification_harness_catalog_version": (
                SYNTHESIS_VERIFICATION_HARNESS_CATALOG_VERSION_V1
            ),
        },
    }


def record_synthesis_harness_run_v1(receipt: dict[str, Any]) -> dict[str, Any]:
    """Append harness receipt to in-process run ledger (newest last)."""
    entry = {
        **receipt,
        "harness_run_id": str(uuid.uuid4()),
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    _harness_run_ledger_v1.append(entry)
    while len(_harness_run_ledger_v1) > _HARNESS_RUN_LEDGER_MAX_V1:
        _harness_run_ledger_v1.pop(0)
    return entry


def list_synthesis_harness_run_ledger_v1() -> list[dict[str, Any]]:
    return list(_harness_run_ledger_v1)


def _run_gp08_schema01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.synthesis.anti_goals import (
        verify_gp08_schema01_schema_file_present_static,
        verify_gp08_schema01_synthesis_job_envelope_forbidden_keys_static,
    )
    from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
        verify_gp08_schema01_synthesis_intelligence_artifact_static,
    )
    from vector.domains.cortex.synthesis.synthesis_job_contract import (
        verify_gp08_schema01_synthesis_workload_intent_registry_static,
    )
    from vector.domains.cortex.synthesis.synthesis_orchestrator import (
        verify_gp08_schema01_synthesis_job_envelope_execution_static,
    )

    return _compose_gate_results_v1(
        "G-P08-SCHEMA-01",
        "synthesis_schema_job_and_artifact",
        [
            verify_gp08_schema01_synthesis_job_envelope_forbidden_keys_static(),
            verify_gp08_schema01_schema_file_present_static(),
            verify_gp08_schema01_synthesis_workload_intent_registry_static(),
            verify_gp08_schema01_synthesis_job_envelope_execution_static(),
            verify_gp08_schema01_synthesis_intelligence_artifact_static(),
        ],
    )


def _run_gp08_cite01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_evidence_binding import (
        verify_gp08_cite01_citation_schema_static,
        verify_gp08_cite01_cite_or_omit_static,
        verify_gp08_cite01_envelope_digest_stable_static,
    )

    return _compose_gate_results_v1(
        "G-P08-CITE-01",
        "synthesis_cite_or_omit",
        [
            verify_gp08_cite01_citation_schema_static(),
            verify_gp08_cite01_cite_or_omit_static(),
            verify_gp08_cite01_envelope_digest_stable_static(),
        ],
    )


def _run_gp08_llm01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_llm_router import (
        verify_gp08_llm01_fake_adapter_determinism_static,
        verify_gp08_llm01_model_route_registry_static,
        verify_gp08_llm01_retrieval_legality_gate_static,
        verify_gp08_llm01_sd_mapping_static,
    )

    return _compose_gate_results_v1(
        "G-P08-LLM-01",
        "synthesis_llm_router",
        [
            verify_gp08_llm01_model_route_registry_static(),
            verify_gp08_llm01_fake_adapter_determinism_static(),
            verify_gp08_llm01_retrieval_legality_gate_static(),
            verify_gp08_llm01_sd_mapping_static(),
        ],
    )


def _run_gp08_prm01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_prompt_assembly import (
        verify_gp08_prm01_context_required_fields_static,
        verify_gp08_prm01_prompt_hash_stable_static,
        verify_gp08_prm01_template_registry_static,
        verify_gp08_prm01_variant_override_law_static,
    )

    return _compose_gate_results_v1(
        "G-P08-PRM-01",
        "synthesis_prompt_assembly",
        [
            verify_gp08_prm01_template_registry_static(),
            verify_gp08_prm01_prompt_hash_stable_static(),
            verify_gp08_prm01_context_required_fields_static(),
            verify_gp08_prm01_variant_override_law_static(),
        ],
    )


def _run_gp08_deg02_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_degradation import (
        verify_gp08_deg02_artifact_taxonomy_apply_static,
        verify_gp08_deg02_rd_to_sd_matrix_static,
        verify_gp08_deg02_sd_multiset_monotonic_static,
    )

    return _compose_gate_results_v1(
        "G-P08-DEG-02",
        "synthesis_degradation_taxonomy",
        [
            verify_gp08_deg02_rd_to_sd_matrix_static(),
            verify_gp08_deg02_sd_multiset_monotonic_static(),
            verify_gp08_deg02_artifact_taxonomy_apply_static(),
        ],
    )


def _run_gp08_replay01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs import (
        run_synthesis_gp08_replay_proof_harness_v1,
    )

    harness = run_synthesis_gp08_replay_proof_harness_v1()
    return {
        "id": "G-P08-REPLAY-01",
        "name": "synthesis_replay_01_double_run_equality",
        "passed": bool(harness.get("passed")),
        "severity": default_severity_for_synthesis_gate_v1("G-P08-REPLAY-01"),
        "detail": {"underlying": harness},
    }


def _run_gp08_eco01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_readiness_economics import (
        verify_gp08_eco01_readiness_economics_clean_profile_static,
        verify_gp08_eco02_readiness_economics_hostile_profile_static,
        verify_gp08_eco03_admin_openapi_path_matrix_static,
    )

    return _compose_gate_results_v1(
        "G-P08-ECO-01",
        "synthesis_readiness_economics_receipt",
        [
            verify_gp08_eco01_readiness_economics_clean_profile_static(),
            verify_gp08_eco02_readiness_economics_hostile_profile_static(),
            verify_gp08_eco03_admin_openapi_path_matrix_static(),
        ],
    )


def _wired_synthesis_gp08_runners_v1() -> dict[str, Callable[[], dict[str, Any]]]:
    from vector.domains.cortex.synthesis.anti_goals import (
        verify_gp08_anti01_synthesis_package_static,
        verify_gp08_anti02_synthesis_ingress_token_rejection_static,
    )
    from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
        verify_gp08_deg01_sd_registry_closed_static,
    )
    from vector.domains.cortex.synthesis.synthesis_control_plane import (
        verify_gp08_cp01_synthesis_control_plane_rbac_static,
    )
    from vector.domains.cortex.synthesis.synthesis_ingress import (
        verify_gp08_ingress01_retrieval_evidence_ingress_static,
    )
    from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
        verify_gp08_leg01_synthesis_legality_matrix_static,
    )
    from vector.domains.cortex.synthesis.synthesis_operator_workflows import (
        verify_gp08_wf01_synthesis_spa_routes_complete_static,
    )
    from vector.domains.cortex.synthesis.synthesis_orchestrator import (
        verify_gp08_fsm01_synthesis_phase_order_static,
    )
    from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
        verify_gp08_replay02_publication_epoch_forward_only_static,
    )
    from vector.domains.cortex.synthesis.synthesis_runtime_legality_matrix import (
        verify_gp08_rlm01_synthesis_runtime_legality_matrix_static_bundle,
    )
    from vector.domains.cortex.synthesis.synthesis_tenant_verification import (
        verify_gp08_tver01_org_graph_synthesis_slice_golden_static,
    )

    return {
        "G-P08-ANTI-01": verify_gp08_anti01_synthesis_package_static,
        "G-P08-ANTI-02": verify_gp08_anti02_synthesis_ingress_token_rejection_static,
        "G-P08-SCHEMA-01": _run_gp08_schema01_bundle_static,
        "G-P08-INGRESS-01": verify_gp08_ingress01_retrieval_evidence_ingress_static,
        "G-P08-LEG-01": verify_gp08_leg01_synthesis_legality_matrix_static,
        "G-P08-CITE-01": _run_gp08_cite01_bundle_static,
        "G-P08-FSM-01": verify_gp08_fsm01_synthesis_phase_order_static,
        "G-P08-LLM-01": _run_gp08_llm01_bundle_static,
        "G-P08-PRM-01": _run_gp08_prm01_bundle_static,
        "G-P08-DEG-01": verify_gp08_deg01_sd_registry_closed_static,
        "G-P08-DEG-02": _run_gp08_deg02_bundle_static,
        "G-P08-REPLAY-01": _run_gp08_replay01_bundle_static,
        "G-P08-REPLAY-02": verify_gp08_replay02_publication_epoch_forward_only_static,
        "G-P08-CP-01": verify_gp08_cp01_synthesis_control_plane_rbac_static,
        "G-P08-TVER-01": verify_gp08_tver01_org_graph_synthesis_slice_golden_static,
        "G-P08-WF-01": verify_gp08_wf01_synthesis_spa_routes_complete_static,
        "G-P08-ECO-01": _run_gp08_eco01_bundle_static,
        "G-P08-RLM-01": verify_gp08_rlm01_synthesis_runtime_legality_matrix_static_bundle,
        "G-P08-CLOSE-01": verify_gp08_close01_synthesis_cert_pack_closure_static,
    }


def list_synthesis_gp08_wired_verification_runners_v1() -> dict[str, Callable[[], dict[str, Any]]]:
    """Return gate id → zero-arg static runner (**G-P08-*** harness wiring)."""
    return dict(_wired_synthesis_gp08_runners_v1())


def verify_synthesis_gp08_wired_runner_gate_ids_match_static() -> dict[str, Any]:
    """Each wired runner's top-level ``id`` matches its catalog key (**G-P08-CLOSE-01** skipped)."""
    errors: list[str] = []
    for gid, fn in _wired_synthesis_gp08_runners_v1().items():
        if gid == "G-P08-CLOSE-01":
            continue
        out = fn()
        rid = out.get("id")
        if rid is not None and rid != gid:
            errors.append(f"{gid}_returned_{rid}")
    return _meta_result("synthesis_gp08_wired_runner_id_match", errors)


def verify_synthesis_gp08_gate_catalog_unique_ids_static() -> dict[str, Any]:
    errors: list[str] = []
    ids = list(SYNTHESIS_GP08_DOCTRINE_GATE_IDS_V1)
    if len(set(ids)) != len(ids):
        errors.append("duplicate_gate_id_in_doctrine_tuple")
    if ids != sorted(ids, key=str):
        errors.append("doctrine_gate_ids_not_sorted")
    return _meta_result("synthesis_gp08_gate_catalog_unique_ids", errors)


def verify_synthesis_gp08_corruption_bundles_subset_static() -> dict[str, Any]:
    errors: list[str] = []
    known = frozenset(SYNTHESIS_GP08_DOCTRINE_GATE_IDS_V1)
    for bundle, members in SYNTHESIS_GP08_CORRUPTION_BUNDLES_V1.items():
        unknown = sorted(members - known)
        if unknown:
            errors.append(f"bundle_{bundle}_unknown:{unknown!r}")
    return _meta_result("synthesis_gp08_corruption_bundles_subset", errors)


def _run_stage_gates_v1(
    gate_ids: Sequence[str],
    *,
    stage: str,
    abort_on_hard_fail: bool,
) -> dict[str, Any]:
    runners = _wired_synthesis_gp08_runners_v1()
    results: list[dict[str, Any]] = []
    hard_fail = False
    for gid in gate_ids:
        out = runners[gid]()
        results.append(out)
        if not out.get("passed") and out.get("severity") == "hard_fail":
            hard_fail = True
            if abort_on_hard_fail:
                break
    return {
        "stage": stage,
        "gate_ids": list(gate_ids),
        "results": results,
        "passed": not hard_fail and all(bool(r.get("passed")) for r in results),
    }


def run_synthesis_gp08_stage_c_replay_gates_v1(
    *,
    abort_on_hard_fail: bool = True,
) -> dict[str, Any]:
    """Execute stage **C** replay gates (**G-P08-REPLAY-01/02**)."""
    from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
        get_synthesis_replay_divergence_total_v1,
    )

    out = _run_stage_gates_v1(
        SYNTHESIS_GP08_STAGE_C_GATE_IDS_V1,
        stage="C",
        abort_on_hard_fail=abort_on_hard_fail,
    )
    out["synthesis_replay_divergence_total"] = get_synthesis_replay_divergence_total_v1()
    return out


def run_synthesis_gp08_wired_verification_stages_v1(
    stages: Sequence[SynthesisGateStageV1],
    *,
    abort_on_hard_fail: bool = True,
    skip_gate_ids: frozenset[str] | None = None,
    record_ledger: bool = True,
) -> dict[str, Any]:
    """Execute wired **G-P08-*** runners for listed stages (stable gate-id order)."""
    runners = _wired_synthesis_gp08_runners_v1()
    order = tuple(dict.fromkeys(stages))
    results: list[dict[str, Any]] = []
    strict = os.environ.get(SYNTHESIS_VERIFICATION_MODE_ENV, "").strip().lower() == "strict"
    skip = skip_gate_ids or frozenset()
    for stage in order:
        base = sorted(
            (
                g
                for g, st in _SYNTHESIS_GATE_STAGE_V1.items()
                if st == stage and g in runners and g not in skip
            ),
            key=str,
        )
        if stage == "Z" and "G-P08-CLOSE-01" in base:
            gate_ids = [g for g in base if g != "G-P08-CLOSE-01"] + ["G-P08-CLOSE-01"]
        else:
            gate_ids = list(base)
        for gid in gate_ids:
            out = runners[gid]()
            results.append({"stage": stage, "gate_id": gid, "result": out})
            sev = out.get("severity") or default_severity_for_synthesis_gate_v1(gid)
            failed = out.get("passed") is False
            if failed and (sev == "hard_fail" or strict) and abort_on_hard_fail:
                body = {
                    "passed": False,
                    "failed_gate_id": gid,
                    "failed_stage": stage,
                    "strict": strict,
                    "synthesis_verification_harness_catalog_version": (
                        SYNTHESIS_VERIFICATION_HARNESS_CATALOG_VERSION_V1
                    ),
                    "results": results,
                }
                if record_ledger:
                    record_synthesis_harness_run_v1(
                        {"run_kind": "wired_stages", "stages": list(order), **body}
                    )
                return body
    body = {
        "passed": True,
        "strict": strict,
        "synthesis_verification_harness_catalog_version": (
            SYNTHESIS_VERIFICATION_HARNESS_CATALOG_VERSION_V1
        ),
        "results": results,
    }
    if record_ledger:
        record_synthesis_harness_run_v1({"run_kind": "wired_stages", "stages": list(order), **body})
    return body


def run_synthesis_gp08_pr_blocking_static_stages_v1(
    *,
    abort_on_hard_fail: bool = True,
    record_ledger: bool = True,
) -> dict[str, Any]:
    """PR-blocking bundle: catalog meta + stages **A+B+C** (testing strategy §CI)."""
    meta_pre = [
        verify_synthesis_gp08_gate_catalog_unique_ids_static(),
        verify_synthesis_gp08_corruption_bundles_subset_static(),
        verify_synthesis_gp08_wired_runner_gate_ids_match_static(),
    ]
    if any(not m.get("passed") for m in meta_pre):
        body = {"passed": False, "phase": "catalog_meta", "meta_results": meta_pre}
        if record_ledger:
            record_synthesis_harness_run_v1({"run_kind": "pr_blocking", **body})
        return body
    stage_a = _run_stage_gates_v1(
        SYNTHESIS_GP08_STAGE_A_GATE_IDS_V1,
        stage="A",
        abort_on_hard_fail=abort_on_hard_fail,
    )
    if not stage_a.get("passed") and abort_on_hard_fail:
        body = {
            "passed": False,
            "stages": ["A"],
            "stage_a": stage_a["results"],
            "meta_results": meta_pre,
        }
        if record_ledger:
            record_synthesis_harness_run_v1({"run_kind": "pr_blocking", **body})
        return body
    stage_b = _run_stage_gates_v1(
        SYNTHESIS_GP08_STAGE_B_GATE_IDS_V1,
        stage="B",
        abort_on_hard_fail=abort_on_hard_fail,
    )
    if not stage_b.get("passed") and abort_on_hard_fail:
        body = {
            "passed": False,
            "stages": ["A", "B"],
            "stage_a": stage_a["results"],
            "stage_b": stage_b["results"],
            "meta_results": meta_pre,
        }
        if record_ledger:
            record_synthesis_harness_run_v1({"run_kind": "pr_blocking", **body})
        return body
    stage_c_out = run_synthesis_gp08_stage_c_replay_gates_v1(abort_on_hard_fail=abort_on_hard_fail)
    passed = (
        bool(stage_a.get("passed"))
        and bool(stage_b.get("passed"))
        and bool(stage_c_out.get("passed"))
    )
    body = {
        "stages": ["A", "B", "C"],
        "stage_a": list(stage_a.get("results") or []),
        "stage_b": list(stage_b.get("results") or []),
        "stage_c": list(stage_c_out.get("results") or []),
        "passed": passed,
        "meta_results": meta_pre,
        "synthesis_replay_divergence_total": stage_c_out.get("synthesis_replay_divergence_total"),
    }
    if record_ledger:
        record_synthesis_harness_run_v1({"run_kind": "pr_blocking", **body})
    return body


def run_synthesis_gp08_ci_full_wired_stages_with_meta_v1(
    *,
    abort_on_hard_fail: bool = False,
    record_ledger: bool = True,
) -> dict[str, Any]:
    """Full **A…E** + **Z** wired pass (incl. **G-P08-CLOSE-01**)."""
    meta_pre = [
        verify_synthesis_gp08_gate_catalog_unique_ids_static(),
        verify_synthesis_gp08_corruption_bundles_subset_static(),
        verify_synthesis_gp08_wired_runner_gate_ids_match_static(),
    ]
    body = run_synthesis_gp08_wired_verification_stages_v1(
        ("A", "B", "C", "D", "E", "Z"),
        abort_on_hard_fail=abort_on_hard_fail,
        record_ledger=False,
    )
    body["meta_results"] = meta_pre
    body["passed"] = bool(body.get("passed")) and all(m.get("passed") for m in meta_pre)
    if record_ledger:
        record_synthesis_harness_run_v1({"run_kind": "ci_full_wired", **body})
    return body


def build_synthesis_verification_harness_catalog_v1() -> dict[str, Any]:
    """Read-only harness catalog for cert pack ``gate_results.json`` excerpts."""
    return {
        "surface_kind": "verification_probe",
        "synthesis_verification_harness_runtime_schema_version": (
            PHASE08_SYNTHESIS_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION
        ),
        "synthesis_verification_harness_catalog_version": (
            SYNTHESIS_VERIFICATION_HARNESS_CATALOG_VERSION_V1
        ),
        "spec_ref": SYNTHESIS_VERIFICATION_HARNESS_SPEC_REF_V1,
        "gate_ids": list(SYNTHESIS_GP08_DOCTRINE_GATE_IDS_V1),
        "gate_stages": dict(_SYNTHESIS_GATE_STAGE_V1),
        "corruption_bundles": {k: sorted(v) for k, v in SYNTHESIS_GP08_CORRUPTION_BUNDLES_V1.items()},
        "pr_blocking_stages": ["A", "B", "C"],
        "synthesis_cert_pack_format_literal_v1": SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
        "run_ledger_count": len(_harness_run_ledger_v1),
    }


def build_synthesis_verification_harness_receipt_v1(
    *,
    run_mode: str = "catalog",
) -> dict[str, Any]:
    """Harness receipt for admin ``verification_probe`` surfaces."""
    catalog = build_synthesis_verification_harness_catalog_v1()
    mode = run_mode.strip().lower()
    run_body: dict[str, Any] | None = None
    if mode == "pr_blocking":
        run_body = run_synthesis_gp08_pr_blocking_static_stages_v1()
    elif mode in ("full", "ci_full", "wired"):
        run_body = run_synthesis_gp08_ci_full_wired_stages_with_meta_v1()
    elif mode == "stage_c":
        run_body = run_synthesis_gp08_stage_c_replay_gates_v1()
    return {
        **catalog,
        "run_mode": mode,
        "harness_run": run_body,
        "run_ledger_tail": list_synthesis_harness_run_ledger_v1()[-5:],
    }


def verify_gp08_rvh01_harness_catalog_covers_spec_gate_table_static() -> dict[str, Any]:
    """P08-26 — doctrine tuple matches testing strategy minimum gate table."""
    errors: list[str] = []
    want = frozenset(
        {
            "G-P08-ANTI-01",
            "G-P08-ANTI-02",
            "G-P08-CITE-01",
            "G-P08-CLOSE-01",
            "G-P08-INGRESS-01",
            "G-P08-LEG-01",
            "G-P08-REPLAY-01",
            "G-P08-REPLAY-02",
            "G-P08-SCHEMA-01",
            "G-P08-TVER-01",
        }
    )
    got = frozenset(SYNTHESIS_GP08_DOCTRINE_GATE_IDS_V1)
    if not want.issubset(got):
        miss = sorted(want - got)
        errors.append(f"catalog_missing_minimum_gates:{miss!r}")
    return {
        "id": "P08-26-rvh-catalog",
        "name": "gp08_rvh01_harness_catalog_covers_spec_gate_table",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase08_synthesis_verification_harness_runtime_schema_version": (
                PHASE08_SYNTHESIS_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp08_rvh02_pr_blocking_bundle_passes_static() -> dict[str, Any]:
    """P08-26 — **STAGE-A…C** + catalog meta green."""
    body = run_synthesis_gp08_pr_blocking_static_stages_v1(record_ledger=False)
    return {
        "id": "P08-26-rvh-pr-blocking",
        "name": "gp08_rvh02_pr_blocking_bundle_passes",
        "passed": bool(body.get("passed")),
        "severity": "hard_fail",
        "detail": {"underlying": body},
    }


def verify_gp08_rvh03_full_stage_az_includes_close_static() -> dict[str, Any]:
    """P08-26 — full **A…E** + **Z** wired pass."""
    body = run_synthesis_gp08_ci_full_wired_stages_with_meta_v1(record_ledger=False)
    return {
        "id": "P08-26-rvh-full-az",
        "name": "gp08_rvh03_full_stage_az_includes_close",
        "passed": bool(body.get("passed")),
        "severity": "hard_fail",
        "detail": {"underlying": body},
    }


def verify_gp08_rvh04_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = ("/admin/catalog/cortex/synthesis/verification-harness",)
    if SYNTHESIS_VERIFICATION_HARNESS_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    return {
        "id": "P08-26-rvh-paths",
        "name": "gp08_rvh04_admin_openapi_path_matrix",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_rvh01_synthesis_verification_harness_static_bundle() -> dict[str, Any]:
    """**G-P08-RVH-01** — PR-blocking self-test bundle for harness closure."""
    errors: list[str] = []
    for fn in (
        verify_gp08_rvh01_harness_catalog_covers_spec_gate_table_static,
        verify_gp08_rvh02_pr_blocking_bundle_passes_static,
        verify_gp08_rvh03_full_stage_az_includes_close_static,
        verify_gp08_rvh04_admin_openapi_path_matrix_static,
    ):
        out = fn()
        if not out.get("passed"):
            errors.append(str(out.get("name")))
    return _meta_result("gp08_rvh01_synthesis_verification_harness_static_bundle", errors)
