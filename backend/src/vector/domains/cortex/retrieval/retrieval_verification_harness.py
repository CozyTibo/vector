"""Phase 07 P07-27 — **G-P07-*** verification harness (catalog + wired static runners).

Normative: ``DOCS/cortex/retrieval/phase-07-verification-harness-spec.md`` (gate table + staging **A–Z**).

Owns gate id → **STAGE** row + static ``runner`` map; ``run_retrieval_gp07_pr_blocking_static_stages_v1``
(stages **A+B+C**) and ``run_retrieval_gp07_wired_verification_stages_v1`` for full CI slices.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import Any, Final, Literal

from vector.domains.cortex.retrieval.retrieval_certification_pack import (
    RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
    RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    verify_gp07_close01_retrieval_cert_pack_closure_static,
)

PHASE07_RETRIEVAL_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_VERIFICATION_HARNESS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-verification-harness-spec.md"
)

RETRIEVAL_VERIFICATION_HARNESS_CATALOG_VERSION_V1: Final[int] = 1

RETRIEVAL_VERIFICATION_MODE_ENV: Final[str] = "RETRIEVAL_VERIFICATION_MODE"

RetrievalGateStageV1 = Literal[
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
RetrievalGateSeverityV1 = Literal["hard_fail", "warn"]

RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P07-ADDR-01",
    "G-P07-ANTI-01",
    "G-P07-ANTI-02",
    "G-P07-CLOSE-01",
    "G-P07-CP-01",
    "G-P07-DEG-01",
    "G-P07-ECO-01",
    "G-P07-PROV-01",
    "G-P07-RANK-01",
    "G-P07-REPLAY-01",
    "G-P07-REPLAY-02",
    "G-P07-SCHEMA-01",
    "G-P07-TVER-01",
)

RETRIEVAL_GP07_CORRUPTION_BUNDLES_V1: Final[dict[str, frozenset[str]]] = {
    "replay_surface": frozenset({"G-P07-REPLAY-01", "G-P07-REPLAY-02"}),
    "control_plane_surface": frozenset({"G-P07-CP-01", "G-P07-TVER-01"}),
    "ingress_anti_surface": frozenset({"G-P07-ANTI-01", "G-P07-ANTI-02", "G-P07-SCHEMA-01"}),
}

_WARN_RETRIEVAL_GATES_V1: Final[frozenset[str]] = frozenset()

_RETRIEVAL_GATE_STAGE_V1: Final[dict[str, RetrievalGateStageV1]] = {
    "G-P07-ANTI-01": "A",
    "G-P07-ANTI-02": "A",
    "G-P07-SCHEMA-01": "A",
    "G-P07-ADDR-01": "B",
    "G-P07-RANK-01": "B",
    "G-P07-PROV-01": "B",
    "G-P07-DEG-01": "B",
    "G-P07-REPLAY-01": "C",
    "G-P07-REPLAY-02": "C",
    "G-P07-CP-01": "D",
    "G-P07-TVER-01": "D",
    "G-P07-ECO-01": "E",
    "G-P07-CLOSE-01": "Z",
}

RETRIEVAL_GP07_STAGE_A_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P07-ANTI-01",
    "G-P07-ANTI-02",
    "G-P07-SCHEMA-01",
)

RETRIEVAL_GP07_STAGE_B_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P07-ADDR-01",
    "G-P07-RANK-01",
    "G-P07-PROV-01",
    "G-P07-DEG-01",
)

RETRIEVAL_GP07_STAGE_C_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P07-REPLAY-01",
    "G-P07-REPLAY-02",
)

RETRIEVAL_GP07_STAGE_D_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P07-CP-01",
    "G-P07-TVER-01",
)

RETRIEVAL_GP07_STAGE_E_GATE_IDS_V1: Final[tuple[str, ...]] = ("G-P07-ECO-01",)


def default_severity_for_retrieval_gate_v1(gate_id: str) -> RetrievalGateSeverityV1:
    return "warn" if gate_id in _WARN_RETRIEVAL_GATES_V1 else "hard_fail"


def retrieval_gp07_gate_stage_v1(gate_id: str) -> RetrievalGateStageV1 | None:
    return _RETRIEVAL_GATE_STAGE_V1.get(gate_id)


def list_retrieval_gp07_doctrine_gate_ids_v1() -> tuple[str, ...]:
    return RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1


def _meta_result(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": "retrieval-gp07-harness-meta-v1",
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase07_retrieval_verification_harness_runtime_schema_version": (
                PHASE07_RETRIEVAL_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION
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
        "severity": default_severity_for_retrieval_gate_v1(gate_id),
        "detail": {
            "sub_results": parts,
            "retrieval_verification_harness_catalog_version": (
                RETRIEVAL_VERIFICATION_HARNESS_CATALOG_VERSION_V1
            ),
        },
    }


def _run_gp07_replay01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
        verify_gp07_replay_01_canonical_identity_stable_static,
        verify_gp07_replay_01_double_run_match_static,
        verify_gp07_replay_01_policy_pin_mismatch_static,
    )
    from vector.domains.cortex.retrieval.retrieval_replay_equivalence_proofs import (
        verify_gp07_replay18_golden_double_run_corpus_static,
    )

    return _compose_gate_results_v1(
        "G-P07-REPLAY-01",
        "retrieval_replay_01_double_run_equality",
        [
            verify_gp07_replay_01_canonical_identity_stable_static(),
            verify_gp07_replay_01_double_run_match_static(),
            verify_gp07_replay_01_policy_pin_mismatch_static(),
            verify_gp07_replay18_golden_double_run_corpus_static(),
        ],
    )


def _run_gp07_eco01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.retrieval.retrieval_readiness_economics import (
        verify_gp07_eco01_readiness_economics_clean_profile_static,
        verify_gp07_eco02_readiness_economics_hostile_profile_static,
        verify_gp07_eco03_admin_openapi_path_matrix_static,
    )

    return _compose_gate_results_v1(
        "G-P07-ECO-01",
        "retrieval_readiness_economics_receipt",
        [
            verify_gp07_eco01_readiness_economics_clean_profile_static(),
            verify_gp07_eco02_readiness_economics_hostile_profile_static(),
            verify_gp07_eco03_admin_openapi_path_matrix_static(),
        ],
    )


def _wired_retrieval_gp07_runners_v1() -> dict[str, Callable[[], dict[str, Any]]]:
    from vector.domains.cortex.retrieval.anti_goals import (
        verify_gp07_anti01_retrieval_package_static,
        verify_gp07_anti02_retrieval_ingress_token_rejection_static,
        verify_gp07_schema01_retrieval_query_envelope_forbidden_keys_static,
    )
    from vector.domains.cortex.retrieval.retrieval_addressing import (
        verify_gp07_addr01_golden_corpus_static,
    )
    from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
        verify_gp07_deg01_rd_registry_closed_static,
    )
    from vector.domains.cortex.retrieval.retrieval_control_plane import (
        verify_gp07_cp01_retrieval_control_plane_rbac_static,
    )
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        verify_gp07_replay02_index_permutation_invariance_static,
    )
    from vector.domains.cortex.retrieval.retrieval_provenance_evidence import (
        verify_gp07_prov01_provenance_field_checklist_static,
    )
    from vector.domains.cortex.retrieval.retrieval_ranking_selection import (
        verify_gp07_rank01_no_float_scores_static,
    )
    from vector.domains.cortex.retrieval.retrieval_tenant_verification_slice import (
        verify_gp07_tver01_org_graph_retrieval_slice_golden_static,
    )

    return {
        "G-P07-ANTI-01": verify_gp07_anti01_retrieval_package_static,
        "G-P07-ANTI-02": verify_gp07_anti02_retrieval_ingress_token_rejection_static,
        "G-P07-SCHEMA-01": verify_gp07_schema01_retrieval_query_envelope_forbidden_keys_static,
        "G-P07-ADDR-01": verify_gp07_addr01_golden_corpus_static,
        "G-P07-RANK-01": verify_gp07_rank01_no_float_scores_static,
        "G-P07-PROV-01": verify_gp07_prov01_provenance_field_checklist_static,
        "G-P07-DEG-01": verify_gp07_deg01_rd_registry_closed_static,
        "G-P07-REPLAY-01": _run_gp07_replay01_bundle_static,
        "G-P07-REPLAY-02": verify_gp07_replay02_index_permutation_invariance_static,
        "G-P07-CP-01": verify_gp07_cp01_retrieval_control_plane_rbac_static,
        "G-P07-TVER-01": verify_gp07_tver01_org_graph_retrieval_slice_golden_static,
        "G-P07-ECO-01": _run_gp07_eco01_bundle_static,
        "G-P07-CLOSE-01": verify_gp07_close01_retrieval_cert_pack_closure_static,
    }


def list_retrieval_gp07_wired_verification_runners_v1() -> dict[str, Callable[[], dict[str, Any]]]:
    """Return gate id → zero-arg static runner (**G-P07-*** harness wiring)."""
    return dict(_wired_retrieval_gp07_runners_v1())


def verify_retrieval_gp07_wired_runner_gate_ids_match_static() -> dict[str, Any]:
    """Each wired runner's top-level ``id`` matches its catalog key (**G-P07-CLOSE-01** skipped)."""
    errors: list[str] = []
    for gid, fn in _wired_retrieval_gp07_runners_v1().items():
        if gid == "G-P07-CLOSE-01":
            continue
        out = fn()
        rid = out.get("id")
        if rid is not None and rid != gid:
            errors.append(f"{gid}_returned_{rid}")
    return _meta_result("retrieval_gp07_wired_runner_id_match", errors)


def verify_retrieval_gp07_gate_catalog_unique_ids_static() -> dict[str, Any]:
    errors: list[str] = []
    ids = list(RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1)
    if len(set(ids)) != len(ids):
        errors.append("duplicate_gate_id_in_doctrine_tuple")
    if ids != sorted(ids, key=str):
        errors.append("doctrine_gate_ids_not_sorted")
    return _meta_result("retrieval_gp07_gate_catalog_unique_ids", errors)


def verify_retrieval_gp07_corruption_bundles_subset_static() -> dict[str, Any]:
    errors: list[str] = []
    known = frozenset(RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1)
    for bundle, members in RETRIEVAL_GP07_CORRUPTION_BUNDLES_V1.items():
        unknown = sorted(members - known)
        if unknown:
            errors.append(f"bundle_{bundle}_unknown:{unknown!r}")
    return _meta_result("retrieval_gp07_corruption_bundles_subset", errors)


def _run_stage_gates_v1(
    gate_ids: Sequence[str],
    *,
    stage: str,
    abort_on_hard_fail: bool,
) -> dict[str, Any]:
    runners = _wired_retrieval_gp07_runners_v1()
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


def run_retrieval_gp07_stage_c_replay_gates_v1(
    *,
    abort_on_hard_fail: bool = True,
) -> dict[str, Any]:
    """Execute stage **C** replay gates (**G-P07-REPLAY-01/02**)."""
    from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
        get_retrieval_replay_divergence_total_v1,
    )

    out = _run_stage_gates_v1(
        RETRIEVAL_GP07_STAGE_C_GATE_IDS_V1,
        stage="C",
        abort_on_hard_fail=abort_on_hard_fail,
    )
    out["retrieval_replay_divergence_total"] = get_retrieval_replay_divergence_total_v1()
    return out


def run_retrieval_gp07_wired_verification_stages_v1(
    stages: Sequence[RetrievalGateStageV1],
    *,
    abort_on_hard_fail: bool = True,
    skip_gate_ids: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Execute wired **G-P07-*** runners for listed stages (stable gate-id order)."""
    runners = _wired_retrieval_gp07_runners_v1()
    order = tuple(dict.fromkeys(stages))
    results: list[dict[str, Any]] = []
    strict = os.environ.get(RETRIEVAL_VERIFICATION_MODE_ENV, "").strip().lower() == "strict"
    skip = skip_gate_ids or frozenset()
    for stage in order:
        base = sorted(
            (
                g
                for g, st in _RETRIEVAL_GATE_STAGE_V1.items()
                if st == stage and g in runners and g not in skip
            ),
            key=str,
        )
        if stage == "Z" and "G-P07-CLOSE-01" in base:
            gate_ids = [g for g in base if g != "G-P07-CLOSE-01"] + ["G-P07-CLOSE-01"]
        else:
            gate_ids = list(base)
        for gid in gate_ids:
            out = runners[gid]()
            results.append({"stage": stage, "gate_id": gid, "result": out})
            sev = out.get("severity") or default_severity_for_retrieval_gate_v1(gid)
            failed = out.get("passed") is False
            if failed and (sev == "hard_fail" or strict) and abort_on_hard_fail:
                return {
                    "passed": False,
                    "failed_gate_id": gid,
                    "failed_stage": stage,
                    "strict": strict,
                    "retrieval_verification_harness_catalog_version": (
                        RETRIEVAL_VERIFICATION_HARNESS_CATALOG_VERSION_V1
                    ),
                    "results": results,
                }
    return {
        "passed": True,
        "strict": strict,
        "retrieval_verification_harness_catalog_version": (
            RETRIEVAL_VERIFICATION_HARNESS_CATALOG_VERSION_V1
        ),
        "results": results,
    }


def run_retrieval_gp07_pr_blocking_static_stages_v1(
    *,
    abort_on_hard_fail: bool = True,
) -> dict[str, Any]:
    """PR-blocking bundle: catalog meta + stages **A+B+C** (harness spec §PR blocking)."""
    meta_pre = [
        verify_retrieval_gp07_gate_catalog_unique_ids_static(),
        verify_retrieval_gp07_corruption_bundles_subset_static(),
        verify_retrieval_gp07_wired_runner_gate_ids_match_static(),
    ]
    if any(not m.get("passed") for m in meta_pre):
        return {"passed": False, "phase": "catalog_meta", "meta_results": meta_pre}
    stage_a = _run_stage_gates_v1(
        RETRIEVAL_GP07_STAGE_A_GATE_IDS_V1,
        stage="A",
        abort_on_hard_fail=abort_on_hard_fail,
    )
    if not stage_a.get("passed") and abort_on_hard_fail:
        return {
            "passed": False,
            "stages": ["A"],
            "stage_a": stage_a["results"],
            "meta_results": meta_pre,
        }
    stage_b = _run_stage_gates_v1(
        RETRIEVAL_GP07_STAGE_B_GATE_IDS_V1,
        stage="B",
        abort_on_hard_fail=abort_on_hard_fail,
    )
    if not stage_b.get("passed") and abort_on_hard_fail:
        return {
            "passed": False,
            "stages": ["A", "B"],
            "stage_a": stage_a["results"],
            "stage_b": stage_b["results"],
            "meta_results": meta_pre,
        }
    stage_c_out = run_retrieval_gp07_stage_c_replay_gates_v1(abort_on_hard_fail=abort_on_hard_fail)
    passed = (
        bool(stage_a.get("passed"))
        and bool(stage_b.get("passed"))
        and bool(stage_c_out.get("passed"))
    )
    return {
        "stages": ["A", "B", "C"],
        "stage_a": list(stage_a.get("results") or []),
        "stage_b": list(stage_b.get("results") or []),
        "stage_c": list(stage_c_out.get("results") or []),
        "passed": passed,
        "meta_results": meta_pre,
        "retrieval_replay_divergence_total": stage_c_out.get("retrieval_replay_divergence_total"),
    }


def run_retrieval_gp07_ci_full_wired_stages_with_meta_v1(
    *,
    abort_on_hard_fail: bool = False,
) -> dict[str, Any]:
    """Full **A…E** + **Z** wired pass (incl. **G-P07-CLOSE-01**)."""
    meta_pre = [
        verify_retrieval_gp07_gate_catalog_unique_ids_static(),
        verify_retrieval_gp07_corruption_bundles_subset_static(),
        verify_retrieval_gp07_wired_runner_gate_ids_match_static(),
    ]
    body = run_retrieval_gp07_wired_verification_stages_v1(
        ("A", "B", "C", "D", "E", "Z"),
        abort_on_hard_fail=abort_on_hard_fail,
    )
    body["meta_results"] = meta_pre
    body["passed"] = body.get("passed") and all(m.get("passed") for m in meta_pre)
    return body


def build_retrieval_verification_harness_catalog_v1() -> dict[str, Any]:
    """Read-only harness catalog for cert pack ``gate_results.json`` excerpts."""
    return {
        "retrieval_verification_harness_runtime_schema_version": (
            PHASE07_RETRIEVAL_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION
        ),
        "retrieval_verification_harness_catalog_version": (
            RETRIEVAL_VERIFICATION_HARNESS_CATALOG_VERSION_V1
        ),
        "spec_ref": RETRIEVAL_VERIFICATION_HARNESS_SPEC_REF_V1,
        "gate_ids": list(RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1),
        "gate_stages": dict(_RETRIEVAL_GATE_STAGE_V1),
        "corruption_bundles": {
            k: sorted(v) for k, v in RETRIEVAL_GP07_CORRUPTION_BUNDLES_V1.items()
        },
        "pr_blocking_stages": ["A", "B", "C"],
        "retrieval_cert_pack_format_literal_v1": RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
    }


def verify_gp07_rvh01_harness_catalog_covers_spec_gate_table_static() -> dict[str, Any]:
    """P07-27 — doctrine tuple matches harness spec minimum gate table."""
    errors: list[str] = []
    want = frozenset(
        {
            "G-P07-ADDR-01",
            "G-P07-ANTI-01",
            "G-P07-ANTI-02",
            "G-P07-CLOSE-01",
            "G-P07-CP-01",
            "G-P07-DEG-01",
            "G-P07-ECO-01",
            "G-P07-PROV-01",
            "G-P07-RANK-01",
            "G-P07-REPLAY-01",
            "G-P07-REPLAY-02",
            "G-P07-SCHEMA-01",
            "G-P07-TVER-01",
        }
    )
    got = frozenset(RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1)
    if got != want:
        miss = sorted(want - got)
        extra = sorted(got - want)
        errors.append(f"catalog_mismatch_missing={miss!r}_extra={extra!r}")
    return {
        "id": "P07-27-rvh-catalog",
        "name": "gp07_rvh01_harness_catalog_covers_spec_gate_table",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase07_retrieval_verification_harness_runtime_schema_version": (
                PHASE07_RETRIEVAL_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp07_rvh02_pr_blocking_bundle_passes_static() -> dict[str, Any]:
    """P07-27 — **STAGE-A…C** + catalog meta green."""
    body = run_retrieval_gp07_pr_blocking_static_stages_v1()
    return {
        "id": "P07-27-rvh-pr-blocking",
        "name": "gp07_rvh02_pr_blocking_bundle_passes",
        "passed": bool(body.get("passed")),
        "severity": "hard_fail",
        "detail": {"underlying": body},
    }


def verify_gp07_rvh03_full_stage_az_includes_close_static() -> dict[str, Any]:
    """P07-27 — full **A…E** + **Z** wired pass."""
    body = run_retrieval_gp07_ci_full_wired_stages_with_meta_v1()
    return {
        "id": "P07-27-rvh-full-az",
        "name": "gp07_rvh03_full_stage_az_includes_close",
        "passed": bool(body.get("passed")),
        "severity": "hard_fail",
        "detail": {"underlying": body},
    }
