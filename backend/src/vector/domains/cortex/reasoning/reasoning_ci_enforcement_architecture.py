"""Phase 06 P06-31 — **G-P06-*** CI enforcement architecture (STAGE **A…Z** row topology).

Normative: ``DOCS/cortex/reasoning/reasoning-verification-harness-spec.md`` §Staging (mirror
``DOCS/cortex/05-traversal/phase-05-ci-enforcement-architecture.md`` ordering intent).

Owns the **full** STAGE row map (every letter **A–Z**, empty rows permitted), **PR-blocking**
stage slice constants, and bundled runners that attach CI-architecture metadata.
"""

from __future__ import annotations

from typing import Any, Final, cast

from vector.domains.cortex.reasoning.reasoning_verification_harness import (
    REASONING_GP06_DOCTRINE_GATE_IDS_V1,
    ReasoningGateStageV1,
    default_severity_for_reasoning_gate_v1,
    list_reasoning_gp06_wired_verification_runners_v1,
    reasoning_gp06_gate_stage_v1,
    run_reasoning_gp06_pr_blocking_static_stages_v1,
    run_reasoning_gp06_wired_verification_stages_v1,
    verify_reasoning_gp06_corruption_bundles_subset_static,
    verify_reasoning_gp06_gate_catalog_unique_ids_static,
    verify_reasoning_gp06_wired_runner_gate_ids_match_static,
)

PHASE06_REASONING_CI_ENFORCEMENT_ARCHITECTURE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

REASONING_CI_ENFORCEMENT_ARCH_PHASE05_REF_V1: Final[str] = (
    "DOCS/cortex/05-traversal/phase-05-ci-enforcement-architecture.md"
)
REASONING_CI_ENFORCEMENT_ARCH_HARNESS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/reasoning/reasoning-verification-harness-spec.md"
)

# Paraphrase **INVARIANT CI-01** from Phase **05** CI arch (same release-surface discipline).
REASONING_GP06_CI_INVARIANT_PARALLEL_STAGES_V1: Final[str] = (
    "INVARIANT CI-01 (Reasoning): MUST NOT parallelize G-P06 stage bundles across different "
    "commit SHAs for the same release surface."
)

_REASONING_CI_STAGE_LETTERS_ORDER_V1: Final[str] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# PR / merge-blocking static slice (analogous to OCTS **STAGE-A…D** on PR paths).
REASONING_GP06_CI_PR_BLOCKING_STAGES_V1: Final[tuple[ReasoningGateStageV1, ...]] = (
    "A",
    "B",
    "C",
    "D",
)

# Full wired static bundle incl. **G-P06-BP-01** (E) and **G-P06-CLOSE-01** (Z).
REASONING_GP06_CI_FULL_STATIC_STAGES_V1: Final[tuple[ReasoningGateStageV1, ...]] = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "Z",
)


def list_reasoning_gp06_ci_stage_letters_ordered_v1() -> tuple[str, ...]:
    """Return **A…Z** in stable lexicographic CI order."""
    return tuple(_REASONING_CI_STAGE_LETTERS_ORDER_V1)


def reasoning_gp06_ci_full_stage_row_map_v1() -> dict[str, tuple[str, ...]]:
    """Full **A–Z** STAGE row map: doctrine **G-P06-*** ids per row (sorted); empty rows OK."""
    rows: dict[str, tuple[str, ...]] = {}
    for stage in _REASONING_CI_STAGE_LETTERS_ORDER_V1:
        gids = sorted(
            gid
            for gid in REASONING_GP06_DOCTRINE_GATE_IDS_V1
            if reasoning_gp06_gate_stage_v1(gid) == stage
        )
        rows[stage] = tuple(gids)
    return rows


def _cia_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": "reasoning-gp06-ci-arch-meta-v1",
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase06_reasoning_ci_enforcement_architecture_runtime_schema_version": (
                PHASE06_REASONING_CI_ENFORCEMENT_ARCHITECTURE_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp06_cia01_full_stage_row_partition_covers_doctrine_static() -> dict[str, Any]:
    """Every doctrine gate has exactly one STAGE row; rows are disjoint and cover the tuple."""
    errors: list[str] = []
    for gid in REASONING_GP06_DOCTRINE_GATE_IDS_V1:
        if reasoning_gp06_gate_stage_v1(gid) is None:
            errors.append(f"missing_stage_assignment:{gid}")
    row = reasoning_gp06_ci_full_stage_row_map_v1()
    seen: set[str] = set()
    for _stage, gids in row.items():
        for g in gids:
            if g in seen:
                errors.append(f"duplicate_gate_in_rows:{g}")
            seen.add(g)
    if seen != frozenset(REASONING_GP06_DOCTRINE_GATE_IDS_V1):
        errors.append("row_union_mismatch_doctrine_tuple")
    if set(row.keys()) != set(_REASONING_CI_STAGE_LETTERS_ORDER_V1):
        errors.append("row_map_keys_not_full_az")
    return _cia_meta("gp06_cia01_full_stage_row_partition_covers_doctrine", errors)


def verify_gp06_cia02_pr_blocking_stages_match_constant_and_underlying_static() -> dict[str, Any]:
    errors: list[str] = []
    body = run_reasoning_gp06_pr_blocking_static_stages_v1()
    if not body.get("passed"):
        errors.append("pr_blocking_underlying_failed")
    else:
        order: list[str] = []
        for r in body.get("results", []):
            st = r.get("stage")
            if not isinstance(st, str):
                errors.append("result_missing_stage")
                break
            if not order or order[-1] != st:
                order.append(st)
        if tuple(order) != REASONING_GP06_CI_PR_BLOCKING_STAGES_V1:
            errors.append(f"pr_results_stage_order_mismatch:{tuple(order)!r}")
    return _cia_meta("gp06_cia02_pr_blocking_stages_match_constant", errors)


def verify_gp06_cia03_severity_defaults_hard_fail_all_doctrine_static() -> dict[str, Any]:
    errors: list[str] = []
    for gid in REASONING_GP06_DOCTRINE_GATE_IDS_V1:
        if default_severity_for_reasoning_gate_v1(gid) != "hard_fail":
            errors.append(f"non_hard_fail_default:{gid}")
    return _cia_meta("gp06_cia03_severity_defaults_hard_fail_all_doctrine", errors)


def verify_gp06_cia04_wired_runner_keys_equal_doctrine_static() -> dict[str, Any]:
    errors: list[str] = []
    want = frozenset(REASONING_GP06_DOCTRINE_GATE_IDS_V1)
    got = frozenset(list_reasoning_gp06_wired_verification_runners_v1().keys())
    if want != got:
        miss = sorted(want - got)
        extra = sorted(got - want)
        errors.append(f"runner_key_mismatch_missing={miss!r}_extra={extra!r}")
    return _cia_meta("gp06_cia04_wired_runner_keys_equal_doctrine", errors)


def verify_gp06_cia05_full_az_topology_including_empty_rows_passes_static() -> dict[str, Any]:
    """Run **A…Z** in order; **F–Y** are empty; must still pass (topology oracle)."""
    stages = cast(
        tuple[ReasoningGateStageV1, ...],
        tuple(_REASONING_CI_STAGE_LETTERS_ORDER_V1),
    )
    body = run_reasoning_gp06_wired_verification_stages_v1(stages)
    passed = bool(body.get("passed"))
    return {
        "id": "P06-31-cia-full-az-topology",
        "name": "gp06_cia05_full_az_topology_including_empty_rows_passes",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "underlying": body,
            "phase06_reasoning_ci_enforcement_architecture_runtime_schema_version": (
                PHASE06_REASONING_CI_ENFORCEMENT_ARCHITECTURE_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp06_cia06_close_gate_is_last_in_stage_z_static() -> dict[str, Any]:
    """**G-P06-CLOSE-01** is assigned **Z** and runs last in the **Z** execution slice."""
    errors: list[str] = []
    if reasoning_gp06_gate_stage_v1("G-P06-CLOSE-01") != "Z":
        errors.append("close_not_assigned_stage_z")
    body = run_reasoning_gp06_wired_verification_stages_v1(("Z",))
    if not body.get("passed"):
        errors.append("stage_z_run_failed")
    else:
        res = body.get("results", [])
        if not res or res[-1].get("gate_id") != "G-P06-CLOSE-01":
            errors.append(f"close_not_last_in_z_execution:{res!r}")
    return _cia_meta("gp06_cia06_close_gate_is_last_in_stage_z", errors)


def verify_gp06_cia07_phase05_doc_anchor_present_static() -> dict[str, Any]:
    errors: list[str] = []
    if "05-traversal" not in REASONING_CI_ENFORCEMENT_ARCH_PHASE05_REF_V1:
        errors.append("phase05_ref_missing_traversal_segment")
    harness_ref = REASONING_CI_ENFORCEMENT_ARCH_HARNESS_SPEC_REF_V1
    if "reasoning-verification-harness-spec" not in harness_ref:
        errors.append("harness_spec_ref_drift")
    return _cia_meta("gp06_cia07_phase05_doc_anchor_present", errors)


def verify_gp06_cia08_ci_invariant_literal_frozen_static() -> dict[str, Any]:
    errors: list[str] = []
    if "parallel" not in REASONING_GP06_CI_INVARIANT_PARALLEL_STAGES_V1.lower():
        errors.append("invariant_literal_missing_parallel_keyword")
    return _cia_meta("gp06_cia08_ci_invariant_literal_frozen", errors)


def _catalog_meta_pre_v1() -> list[dict[str, Any]]:
    return [
        verify_reasoning_gp06_gate_catalog_unique_ids_static(),
        verify_reasoning_gp06_corruption_bundles_subset_static(),
        verify_reasoning_gp06_wired_runner_gate_ids_match_static(),
    ]


def run_reasoning_gp06_ci_pr_blocking_bundle_v1() -> dict[str, Any]:
    """PR-blocking bundle with CI-architecture metadata (wraps harness PR runner)."""
    out = run_reasoning_gp06_pr_blocking_static_stages_v1()
    return {
        **out,
        "reasoning_gp06_ci_pr_blocking_stages_v1": REASONING_GP06_CI_PR_BLOCKING_STAGES_V1,
        "phase06_reasoning_ci_enforcement_architecture_runtime_schema_version": (
            PHASE06_REASONING_CI_ENFORCEMENT_ARCHITECTURE_RUNTIME_SCHEMA_VERSION
        ),
    }


def run_reasoning_gp06_ci_full_wired_stages_with_meta_v1(
    *,
    abort_on_hard_fail: bool = True,
) -> dict[str, Any]:
    """Catalog meta + **STAGE-A…E,Z** wired gates (breakpoint + close)."""
    meta_pre = _catalog_meta_pre_v1()
    if any(not m.get("passed") for m in meta_pre):
        return {
            "passed": False,
            "phase": "catalog_meta",
            "meta_results": meta_pre,
            "reasoning_gp06_ci_full_static_stages_v1": REASONING_GP06_CI_FULL_STATIC_STAGES_V1,
            "phase06_reasoning_ci_enforcement_architecture_runtime_schema_version": (
                PHASE06_REASONING_CI_ENFORCEMENT_ARCHITECTURE_RUNTIME_SCHEMA_VERSION
            ),
        }
    body = run_reasoning_gp06_wired_verification_stages_v1(
        REASONING_GP06_CI_FULL_STATIC_STAGES_V1,
        abort_on_hard_fail=abort_on_hard_fail,
    )
    return {
        **body,
        "meta_results": meta_pre,
        "reasoning_gp06_ci_full_static_stages_v1": REASONING_GP06_CI_FULL_STATIC_STAGES_V1,
        "phase06_reasoning_ci_enforcement_architecture_runtime_schema_version": (
            PHASE06_REASONING_CI_ENFORCEMENT_ARCHITECTURE_RUNTIME_SCHEMA_VERSION
        ),
    }


def run_reasoning_gp06_ci_full_az_topology_with_meta_v1(
    *,
    abort_on_hard_fail: bool = True,
) -> dict[str, Any]:
    """Catalog meta + full **A…Z** topology (empty intermediate rows)."""
    meta_pre = _catalog_meta_pre_v1()
    if any(not m.get("passed") for m in meta_pre):
        return {
            "passed": False,
            "phase": "catalog_meta",
            "meta_results": meta_pre,
            "reasoning_gp06_ci_topology_stages_v1": tuple(_REASONING_CI_STAGE_LETTERS_ORDER_V1),
            "phase06_reasoning_ci_enforcement_architecture_runtime_schema_version": (
                PHASE06_REASONING_CI_ENFORCEMENT_ARCHITECTURE_RUNTIME_SCHEMA_VERSION
            ),
        }
    stages = cast(
        tuple[ReasoningGateStageV1, ...],
        tuple(_REASONING_CI_STAGE_LETTERS_ORDER_V1),
    )
    body = run_reasoning_gp06_wired_verification_stages_v1(
        stages,
        abort_on_hard_fail=abort_on_hard_fail,
    )
    return {
        **body,
        "meta_results": meta_pre,
        "reasoning_gp06_ci_topology_stages_v1": stages,
        "phase06_reasoning_ci_enforcement_architecture_runtime_schema_version": (
            PHASE06_REASONING_CI_ENFORCEMENT_ARCHITECTURE_RUNTIME_SCHEMA_VERSION
        ),
    }
