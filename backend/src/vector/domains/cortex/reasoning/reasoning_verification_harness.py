"""Phase 06 P06-29 — **G-P06-*** verification harness (catalog + wired static runners).

Normative: ``DOCS/cortex/reasoning/reasoning-verification-harness-spec.md`` §1 (gate table),
``DOCS/cortex/05-traversal/phase-05-ci-enforcement-architecture.md`` (staging **A–Z** pattern,
mirrored for TCRE harness execution).

This module owns the **single** map from **G-P06-*** gate id → default **STAGE** row (**A…Z**;
only **A,B,C,D,E,Z** carry gates in v1) + static ``runner`` (callable returning
``{id, name, passed, severity, detail}``). Composite gates bundle
existing ``verify_gp06_*`` predicates from prior P06 steps.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import Any, Final, Literal

from vector.domains.cortex.traversal.certification_pack import OCTS_CERT_PACK_FORMAT_LITERAL

from vector.domains.cortex.reasoning.reasoning_certification_pack import (
    TCRE_CERT_PACK_FORMAT_LITERAL_V1,
    TCRE_CERT_PACK_MANIFEST_FORMAT_KEY_V1,
    TCRE_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    verify_gp06_close01_tcre_cert_pack_closure_static,
    verify_gp06_close01_tcre_cert_pack_shape_reference_static,
)

PHASE06_REASONING_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

REASONING_VERIFICATION_HARNESS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/reasoning/reasoning-verification-harness-spec.md"
)

REASONING_VERIFICATION_HARNESS_CATALOG_VERSION_V1: Final[int] = 1

REASONING_VERIFICATION_MODE_ENV: Final[str] = "REASONING_VERIFICATION_MODE"

ReasoningGateStageV1 = Literal[
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
ReasoningGateSeverityV1 = Literal["hard_fail", "warn"]

# Back-compat name: required tar members match **OCTS-CERT-PACK-1** §3 (``reasoning_certification_pack``).
OCTS_CERT_PACK_REQUIRED_ROOT_FILES_V1: Final[tuple[str, ...]] = TCRE_CERT_PACK_REQUIRED_ROOT_FILES_V1

REASONING_GP06_DOCTRINE_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P06-AMB-01",
    "G-P06-ANTI-01",
    "G-P06-BP-01",
    "G-P06-CAUS-01",
    "G-P06-CHRON-01",
    "G-P06-CLOSE-01",
    "G-P06-POL-01",
    "G-P06-PROV-01",
    "G-P06-REPLAY-01",
)

REASONING_GP06_CORRUPTION_BUNDLES_V1: Final[dict[str, frozenset[str]]] = {
    "replay_equivalence_surface": frozenset({"G-P06-REPLAY-01", "G-P06-PROV-01"}),
    "chronology_causal_surface": frozenset({"G-P06-CHRON-01", "G-P06-CAUS-01"}),
}

_WARN_REASONING_GATES_V1: Final[frozenset[str]] = frozenset()

_REASONING_GATE_STAGE_V1: Final[dict[str, ReasoningGateStageV1]] = {
    "G-P06-ANTI-01": "A",
    "G-P06-POL-01": "B",
    "G-P06-PROV-01": "B",
    "G-P06-CHRON-01": "C",
    "G-P06-CAUS-01": "C",
    "G-P06-REPLAY-01": "D",
    "G-P06-AMB-01": "D",
    "G-P06-BP-01": "E",
    "G-P06-CLOSE-01": "Z",
}


def default_severity_for_reasoning_gate_v1(gate_id: str) -> ReasoningGateSeverityV1:
    return "warn" if gate_id in _WARN_REASONING_GATES_V1 else "hard_fail"


def reasoning_gp06_gate_stage_v1(gate_id: str) -> ReasoningGateStageV1 | None:
    return _REASONING_GATE_STAGE_V1.get(gate_id)


def list_reasoning_gp06_doctrine_gate_ids_v1() -> tuple[str, ...]:
    return REASONING_GP06_DOCTRINE_GATE_IDS_V1


def _meta_result(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": "reasoning-gp06-harness-meta-v1",
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase06_reasoning_verification_harness_runtime_schema_version": (
                PHASE06_REASONING_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_reasoning_gp06_gate_catalog_unique_ids_static() -> dict[str, Any]:
    """Doctrine gate ids are unique and sorted."""
    errors: list[str] = []
    ids = list(REASONING_GP06_DOCTRINE_GATE_IDS_V1)
    if len(set(ids)) != len(ids):
        errors.append("duplicate_gate_id_in_doctrine_tuple")
    if ids != sorted(ids, key=str):
        errors.append("doctrine_gate_ids_not_sorted")
    return _meta_result("reasoning_gp06_gate_catalog_unique_ids", errors)


def verify_reasoning_gp06_corruption_bundles_subset_static() -> dict[str, Any]:
    """Each corruption bundle references only known doctrine gate ids."""
    errors: list[str] = []
    known = frozenset(REASONING_GP06_DOCTRINE_GATE_IDS_V1)
    for bundle, members in REASONING_GP06_CORRUPTION_BUNDLES_V1.items():
        unknown = sorted(members - known)
        if unknown:
            errors.append(f"bundle_{bundle}_unknown:{unknown!r}")
    return _meta_result("reasoning_gp06_corruption_bundles_subset", errors)


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
        "severity": default_severity_for_reasoning_gate_v1(gate_id),
        "detail": {
            "sub_results": parts,
            "reasoning_verification_harness_catalog_version": (
                REASONING_VERIFICATION_HARNESS_CATALOG_VERSION_V1
            ),
        },
    }


def _run_gp06_chron01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.reasoning.chronology_legality import (
        verify_gp06_chron01_default_policy_rows_static,
        verify_gp06_chron02_projection_closure_static,
    )

    return _compose_gate_results_v1(
        "G-P06-CHRON-01",
        "chronology_projection_chron_forb1",
        [
            verify_gp06_chron01_default_policy_rows_static(),
            verify_gp06_chron02_projection_closure_static(),
        ],
    )


def _run_gp06_caus01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.reasoning.causal_reconstruction_substrate import (
        verify_gp06_crs01_coordination_to_tcre_primary_map_static,
        verify_gp06_crs02_reconstruction_requires_confidence_static,
        verify_gp06_crs03_cross_system_weak_only_guard_static,
        verify_gp06_crs04_option_a_rejects_coordination_edge_kind_key_static,
    )

    return _compose_gate_results_v1(
        "G-P06-CAUS-01",
        "tcre_causal_edge_registry_sentinel_rules",
        [
            verify_gp06_crs01_coordination_to_tcre_primary_map_static(),
            verify_gp06_crs02_reconstruction_requires_confidence_static(),
            verify_gp06_crs03_cross_system_weak_only_guard_static(),
            verify_gp06_crs04_option_a_rejects_coordination_edge_kind_key_static(),
        ],
    )


def _run_gp06_replay01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.reasoning.replay_equivalence_proofs import (
        verify_gp06_req01_replay_01_gate_id_oracle_static,
        verify_gp06_req02_permutation_profile_id_literal_static,
        verify_gp06_req03_minimal_bundle_double_run_match_static,
        verify_gp06_req04_chronology_digest_required_when_participates_static,
        verify_gp06_req05_double_run_mismatch_raises_static,
        verify_gp06_req06_causal_only_insufficient_when_receipts_static,
    )

    return _compose_gate_results_v1(
        "G-P06-REPLAY-01",
        "replay_01_digest_double_run_vector",
        [
            verify_gp06_req01_replay_01_gate_id_oracle_static(),
            verify_gp06_req02_permutation_profile_id_literal_static(),
            verify_gp06_req03_minimal_bundle_double_run_match_static(),
            verify_gp06_req04_chronology_digest_required_when_participates_static(),
            verify_gp06_req05_double_run_mismatch_raises_static(),
            verify_gp06_req06_causal_only_insufficient_when_receipts_static(),
        ],
    )


def _run_gp06_amb01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.reasoning.causal_ambiguity_propagation import (
        verify_gp06_amb01_registry_literal_oracle_static,
        verify_gp06_amb05_bundle_happy_path_static,
    )

    return _compose_gate_results_v1(
        "G-P06-AMB-01",
        "reasoning_ambiguity_receipt_registry",
        [
            verify_gp06_amb01_registry_literal_oracle_static(),
            verify_gp06_amb05_bundle_happy_path_static(),
        ],
    )


def _run_gp06_prov01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.reasoning.reasoning_provenance_law import (
        verify_gp06_rpl01_replay_posture_literal_oracle_static,
        verify_gp06_rpl02_minimal_envelope_happy_path_static,
    )

    return _compose_gate_results_v1(
        "G-P06-PROV-01",
        "reasoning_artifact_provenance_envelope",
        [
            verify_gp06_rpl01_replay_posture_literal_oracle_static(),
            verify_gp06_rpl02_minimal_envelope_happy_path_static(),
        ],
    )


def _run_gp06_bp01_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.reasoning.causal_drift_proofs import (
        verify_gp06_cdp01_breakpoint_id_body_key_oracle_static,
        verify_gp06_cdp02_breakpoint_index_sort_stable_static,
    )

    return _compose_gate_results_v1(
        "G-P06-BP-01",
        "breakpoint_index_byte_stable",
        [
            verify_gp06_cdp01_breakpoint_id_body_key_oracle_static(),
            verify_gp06_cdp02_breakpoint_index_sort_stable_static(),
        ],
    )


def _run_gp06_pol01_wrapper_static() -> dict[str, Any]:
    """**G-P06-POL-01** — delegate to default policy pack **G-P06-POL-01** caps predicate."""
    from vector.domains.cortex.reasoning.chronology_degradation_propagation import (
        verify_gp06_deg03_default_policy_caps_static,
    )

    sub = verify_gp06_deg03_default_policy_caps_static()
    return {
        "id": "G-P06-POL-01",
        "name": "active_policy_pack_g_p06_pol01",
        "passed": bool(sub.get("passed")),
        "severity": default_severity_for_reasoning_gate_v1("G-P06-POL-01"),
        "detail": {"underlying": sub},
    }


def _wired_reasoning_gp06_runners_v1() -> dict[str, Callable[[], dict[str, Any]]]:
    from vector.domains.cortex.reasoning.anti_goals import (
        verify_gp06_anti01_reasoning_package_static,
    )

    return {
        "G-P06-ANTI-01": verify_gp06_anti01_reasoning_package_static,
        "G-P06-POL-01": _run_gp06_pol01_wrapper_static,
        "G-P06-PROV-01": _run_gp06_prov01_bundle_static,
        "G-P06-CHRON-01": _run_gp06_chron01_bundle_static,
        "G-P06-CAUS-01": _run_gp06_caus01_bundle_static,
        "G-P06-REPLAY-01": _run_gp06_replay01_bundle_static,
        "G-P06-AMB-01": _run_gp06_amb01_bundle_static,
        "G-P06-BP-01": _run_gp06_bp01_bundle_static,
        "G-P06-CLOSE-01": verify_gp06_close01_tcre_cert_pack_closure_static,
    }


def list_reasoning_gp06_wired_verification_runners_v1() -> dict[str, Callable[[], dict[str, Any]]]:
    """Return gate id → zero-arg static runner (**G-P06-*** harness wiring)."""
    return dict(_wired_reasoning_gp06_runners_v1())


def verify_reasoning_gp06_wired_runner_gate_ids_match_static() -> dict[str, Any]:
    """Each wired runner's top-level ``id`` matches its catalog key (composite gates included).

    **G-P06-CLOSE-01** is skipped: its runner invokes **PR** + **STAGE-Z**, which would recurse into
    the PR meta bundle that includes this id-match check (mirrors **OCTS** ``verify_octs_*``).
    """
    errors: list[str] = []
    for gid, fn in _wired_reasoning_gp06_runners_v1().items():
        if gid == "G-P06-CLOSE-01":
            continue
        out = fn()
        rid = out.get("id")
        if rid is not None and rid != gid:
            errors.append(f"{gid}_returned_{rid}")
    return _meta_result("reasoning_gp06_wired_runner_id_match", errors)


def run_reasoning_gp06_wired_verification_stages_v1(
    stages: Sequence[ReasoningGateStageV1],
    *,
    abort_on_hard_fail: bool = True,
    skip_gate_ids: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Execute wired **G-P06-*** runners whose stage is listed in ``stages`` (stable gate-id order).

    **STAGE-Z** runs **G-P06-CLOSE-01** last when present (mirrors OCTS close ordering).
    """
    runners = _wired_reasoning_gp06_runners_v1()
    order = tuple(dict.fromkeys(stages))
    results: list[dict[str, Any]] = []
    strict = os.environ.get(REASONING_VERIFICATION_MODE_ENV, "").strip().lower() == "strict"
    skip = skip_gate_ids or frozenset()
    for stage in order:
        base = sorted(
            (
                g
                for g, st in _REASONING_GATE_STAGE_V1.items()
                if st == stage and g in runners and g not in skip
            ),
            key=str,
        )
        if stage == "Z" and "G-P06-CLOSE-01" in base:
            gate_ids = [g for g in base if g != "G-P06-CLOSE-01"] + ["G-P06-CLOSE-01"]
        else:
            gate_ids = list(base)
        for gid in gate_ids:
            out = runners[gid]()
            results.append({"stage": stage, "gate_id": gid, "result": out})
            sev = out.get("severity") or default_severity_for_reasoning_gate_v1(gid)
            failed = out.get("passed") is False
            if failed and (sev == "hard_fail" or strict) and abort_on_hard_fail:
                return {
                    "passed": False,
                    "failed_gate_id": gid,
                    "failed_stage": stage,
                    "strict": strict,
                    "reasoning_verification_harness_catalog_version": (
                        REASONING_VERIFICATION_HARNESS_CATALOG_VERSION_V1
                    ),
                    "results": results,
                }
    return {
        "passed": True,
        "strict": strict,
        "reasoning_verification_harness_catalog_version": (
            REASONING_VERIFICATION_HARNESS_CATALOG_VERSION_V1
        ),
        "results": results,
    }


def run_reasoning_gp06_pr_blocking_static_stages_v1() -> dict[str, Any]:
    """PR-style bundle: catalog meta + **STAGE-A** … **STAGE-D** (per harness §Staging intent)."""
    meta_pre = [
        verify_reasoning_gp06_gate_catalog_unique_ids_static(),
        verify_reasoning_gp06_corruption_bundles_subset_static(),
        verify_reasoning_gp06_wired_runner_gate_ids_match_static(),
    ]
    if any(not m.get("passed") for m in meta_pre):
        return {"passed": False, "phase": "catalog_meta", "meta_results": meta_pre}
    body = run_reasoning_gp06_wired_verification_stages_v1(("A", "B", "C", "D"))
    body["meta_results"] = meta_pre
    if not body.get("passed"):
        return body
    return {"passed": True, **body}


def verify_gp06_rvh01_harness_catalog_covers_spec_gate_table_static() -> dict[str, Any]:
    """P06-29 — doctrine tuple matches the §1 **nine** gate ids (stable frozen set)."""
    errors: list[str] = []
    want = frozenset(
        {
            "G-P06-AMB-01",
            "G-P06-ANTI-01",
            "G-P06-BP-01",
            "G-P06-CAUS-01",
            "G-P06-CHRON-01",
            "G-P06-CLOSE-01",
            "G-P06-POL-01",
            "G-P06-PROV-01",
            "G-P06-REPLAY-01",
        }
    )
    got = frozenset(REASONING_GP06_DOCTRINE_GATE_IDS_V1)
    if got != want:
        miss = sorted(want - got)
        extra = sorted(got - want)
        errors.append(f"catalog_mismatch_missing={miss!r}_extra={extra!r}")
    passed = len(errors) == 0
    return {
        "id": "P06-29-rvh-catalog",
        "name": "gp06_rvh01_harness_catalog_covers_spec_gate_table",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase06_reasoning_verification_harness_runtime_schema_version": (
                PHASE06_REASONING_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp06_rvh02_pr_blocking_bundle_passes_static() -> dict[str, Any]:
    """P06-29 — **STAGE-A…D** + catalog meta green (CI-friendly PR slice)."""
    body = run_reasoning_gp06_pr_blocking_static_stages_v1()
    passed = bool(body.get("passed"))
    return {
        "id": "P06-29-rvh-pr-blocking",
        "name": "gp06_rvh02_pr_blocking_bundle_passes",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "underlying": body,
            "phase06_reasoning_verification_harness_runtime_schema_version": (
                PHASE06_REASONING_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp06_rvh03_full_stage_az_includes_close_static() -> dict[str, Any]:
    """P06-29 — full **A…Z** wired pass (incl. **G-P06-BP-01** / **G-P06-CLOSE-01**)."""
    body = run_reasoning_gp06_wired_verification_stages_v1(("A", "B", "C", "D", "E", "Z"))
    passed = bool(body.get("passed"))
    return {
        "id": "P06-29-rvh-full-az",
        "name": "gp06_rvh03_full_stage_az_includes_close",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "underlying": body,
            "phase06_reasoning_verification_harness_runtime_schema_version": (
                PHASE06_REASONING_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }
