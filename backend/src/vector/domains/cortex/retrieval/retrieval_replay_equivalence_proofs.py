"""Phase 07 P07-18 — retrieval replay equivalence proofs harness (**G-P07-REPLAY-01/02**).

Normative: ``DOCS/cortex/retrieval/phase-07-replay-equivalence-retrieval-spec.md``,
``DOCS/cortex/retrieval/phase-07-verification-harness-spec.md`` (stage **C** replay gates).

Wires static runners, golden ``query/replay_equivalence_double_run_v1``, and stage-C harness
entry points consumed by admin replay inspector and CI (PR-blocking stages **A+B+C** subset).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_legality_projection import retrieval_policy_digest_v1
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
    GP07_REPLAY_01_GATE_ID_V1,
    PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_REPLAY_EQUIVALENCE_SPEC_REF_V1,
    RetrievalReplayEquivalenceError,
    build_retrieval_replay_equivalence_twin_diff_v1,
    build_retrieval_replay_inspector_catalog_v1 as _base_retrieval_replay_inspector_catalog_v1,
    compare_gp07_replay_01_double_run_v1,
    compute_retrieval_query_replay_identity_v1,
    get_retrieval_replay_divergence_total_v1,
    verify_gp07_replay_01_canonical_identity_stable_static,
    verify_gp07_replay_01_double_run_match_static,
    verify_gp07_replay_01_policy_pin_mismatch_static,
)

PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_REPLAY02_GATE_ID_V1: Final[str] = "G-P07-REPLAY-02"

RETRIEVAL_REPLAY_EQUIVALENCE_PROOFS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-replay-equivalence-retrieval-spec.md"
)

RETRIEVAL_VERIFICATION_HARNESS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-verification-harness-spec.md"
)

RETRIEVAL_RD_REPLAY_TWIN_V1: Final[str] = "RD-REPLAY-TWIN"

RETRIEVAL_GP07_STAGE_C_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "G-P07-REPLAY-01",
    "G-P07-REPLAY-02",
)

_GOLDEN_V1_PATH_TAIL: Final[tuple[str, ...]] = (
    "tests",
    "vector",
    "domains",
    "cortex",
    "retrieval",
    "retrieval_golden_vectors",
    "v1",
)


class RetrievalReplayEquivalenceProofsError(ValueError):
    """Fail-closed retrieval replay proof / golden harness execution."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def retrieval_replay_omissions_from_twin_diff_v1(
    twin: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Emit ``RD-REPLAY-TWIN`` when **G-P07-REPLAY-01** twin workload diverges."""
    if twin.get("gp07_replay_01_passed") is True:
        return []
    trigger = "gp07_replay_01_double_run"
    if twin.get("hit_count_mismatch"):
        trigger = "hit_count_mismatch"
    elif twin.get("ordering_divergence"):
        trigger = "ordering_divergence"
    elif twin.get("omission_multiset_delta"):
        trigger = "omission_multiset_delta"
    elif twin.get("receipt_digest_a") != twin.get("receipt_digest_b"):
        trigger = "receipt_digest_mismatch"
    return [
        {
            "retrieval_omission_class": RETRIEVAL_RD_REPLAY_TWIN_V1,
            "upstream_trigger": trigger,
            "gate_id": GP07_REPLAY_01_GATE_ID_V1,
        }
    ]


def retrieval_golden_vectors_v1_root() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        candidate = root.joinpath(*_GOLDEN_V1_PATH_TAIL)
        if candidate.is_dir():
            return candidate
        alt = root / "backend" / Path(*_GOLDEN_V1_PATH_TAIL)
        if alt.is_dir():
            return alt
    raise FileNotFoundError("retrieval_golden_vectors/v1 not found")


def load_retrieval_golden_case_v1(case_id: str) -> dict[str, Any]:
    root = retrieval_golden_vectors_v1_root()
    path = root / "cases" / case_id / "case.json"
    if not path.is_file():
        raise FileNotFoundError(f"golden case not found: {case_id}")
    loaded: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise RetrievalReplayEquivalenceProofsError("golden_case_not_object")
    return loaded


def _synthetic_query_result_from_golden_inputs_v1(
    *,
    envelope: Mapping[str, Any],
    hits: Sequence[Mapping[str, Any]],
    omissions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    digest = retrieval_policy_digest_v1()
    replay_id = compute_retrieval_query_replay_identity_v1(
        envelope=envelope,
        retrieval_policy_digest=digest,
        hits=hits,
        omissions=omissions,
    )
    receipt_digest = compute_retrieval_query_replay_identity_v1(
        envelope={"receipt_body": envelope},
        retrieval_policy_digest=digest,
        hits=hits,
        omissions=omissions,
    )
    return {
        PHASE07_REPLAY_IDENTITY_FIELD_V1: replay_id,
        "retrieval_query_receipt": {"receipt_digest": receipt_digest},
        "hits": list(hits),
        "omissions": list(omissions),
    }


def run_retrieval_golden_replay_equivalence_case_v1(case: Mapping[str, Any]) -> dict[str, Any]:
    """Execute static golden double-run for ``query/replay_equivalence_double_run_v1``."""
    inputs = case.get("inputs")
    if not isinstance(inputs, dict):
        raise RetrievalReplayEquivalenceProofsError("golden_case_missing_inputs")
    expected = case.get("expected")
    if not isinstance(expected, dict):
        raise RetrievalReplayEquivalenceProofsError("golden_case_missing_expected")
    envelope = dict(inputs.get("envelope") or {})
    hits = list(inputs.get("hits") or [])
    omissions = list(inputs.get("omissions") or [])
    run_a = _synthetic_query_result_from_golden_inputs_v1(
        envelope=envelope, hits=hits, omissions=omissions
    )
    run_b = _synthetic_query_result_from_golden_inputs_v1(
        envelope=envelope, hits=hits, omissions=omissions
    )
    twin = build_retrieval_replay_equivalence_twin_diff_v1(run_a, run_b)
    try:
        compare_gp07_replay_01_double_run_v1(run_a, run_b)
    except RetrievalReplayEquivalenceError:
        twin["gp07_replay_01_passed"] = False
    if expected.get("gp07_replay_01_passed") is True and not twin.get("gp07_replay_01_passed"):
        raise RetrievalReplayEquivalenceProofsError(
            "expected_gp07_replay_01_pass",
            detail=dict(twin),
        )
    if expected.get("gp07_replay_01_passed") is False and twin.get("gp07_replay_01_passed"):
        raise RetrievalReplayEquivalenceProofsError("expected_gp07_replay_01_fail")
    if expected.get("retrieval_query_replay_identity_match") is True:
        if twin.get("retrieval_query_replay_identity_a") != twin.get(
            "retrieval_query_replay_identity_b"
        ):
            raise RetrievalReplayEquivalenceProofsError("replay_identity_mismatch")
    return {
        "case_id": case.get("case_id"),
        "gate_id": case.get("gate_id"),
        "twin": twin,
        "gp07_replay_01_passed": bool(twin.get("gp07_replay_01_passed")),
    }


def _proof_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": "retrieval-gp07-replay-proofs-meta-v1",
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase07_retrieval_replay_equivalence_proofs_runtime_schema_version": (
                PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION
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
        "severity": "hard_fail",
        "detail": {"sub_results": parts},
    }


def _run_gp07_replay01_bundle_static() -> dict[str, Any]:
    return _compose_gate_results_v1(
        GP07_REPLAY_01_GATE_ID_V1,
        "retrieval_replay_01_double_run_and_identity",
        [
            verify_gp07_replay_01_canonical_identity_stable_static(),
            verify_gp07_replay_01_double_run_match_static(),
            verify_gp07_replay_01_policy_pin_mismatch_static(),
            verify_gp07_replay18_golden_double_run_corpus_static(),
        ],
    )


def _run_gp07_replay02_bundle_static() -> dict[str, Any]:
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        verify_gp07_replay02_index_permutation_invariance_static,
    )

    return _compose_gate_results_v1(
        GP07_REPLAY02_GATE_ID_V1,
        "retrieval_replay_02_index_permutation_invariance",
        [verify_gp07_replay02_index_permutation_invariance_static()],
    )


def _wired_retrieval_gp07_replay_runners_v1() -> dict[str, Callable[[], dict[str, Any]]]:
    return {
        "G-P07-REPLAY-01": _run_gp07_replay01_bundle_static,
        "G-P07-REPLAY-02": _run_gp07_replay02_bundle_static,
    }


def list_retrieval_gp07_stage_c_replay_runners_v1() -> dict[str, Callable[[], dict[str, Any]]]:
    return dict(_wired_retrieval_gp07_replay_runners_v1())


def verify_gp07_replay18_golden_double_run_corpus_static() -> dict[str, Any]:
    """Golden ``query/replay_equivalence_double_run_v1`` — static double-run harness."""
    errors: list[str] = []
    root = retrieval_golden_vectors_v1_root()
    case_id = "query/replay_equivalence_double_run_v1"
    try:
        case = load_retrieval_golden_case_v1(case_id)
        run_retrieval_golden_replay_equivalence_case_v1(case)
        a = run_retrieval_golden_replay_equivalence_case_v1(case)
        b = run_retrieval_golden_replay_equivalence_case_v1(case)
        if a.get("gp07_replay_01_passed") != b.get("gp07_replay_01_passed"):
            errors.append("determinism_replay_failed")
    except (RetrievalReplayEquivalenceProofsError, FileNotFoundError) as exc:
        errors.append(f"{case_id}:{exc}")
    manifest = root / "corpus_manifest.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        case_ids = [
            str(e.get("case_id"))
            for e in data.get("cases", [])
            if isinstance(e, dict) and e.get("case_id")
        ]
        if case_id not in case_ids:
            errors.append("replay_case_missing_from_manifest")
    else:
        errors.append("missing_corpus_manifest")
    return {
        "id": GP07_REPLAY_01_GATE_ID_V1,
        "name": "gp07_replay18_golden_double_run_corpus",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors, "golden_root": str(root), "case_id": case_id},
    }


def verify_gp07_replay18_twin_failure_emits_rd_replay_twin_static() -> dict[str, Any]:
    errors: list[str] = []
    twin = {
        "gp07_replay_01_passed": False,
        "hit_count_mismatch": True,
        "ordering_divergence": False,
        "omission_multiset_delta": False,
        "receipt_digest_a": "a" * 64,
        "receipt_digest_b": "b" * 64,
    }
    rows = retrieval_replay_omissions_from_twin_diff_v1(twin)
    if not rows or rows[0].get("retrieval_omission_class") != RETRIEVAL_RD_REPLAY_TWIN_V1:
        errors.append("expected_rd_replay_twin")
    ok_twin = {**twin, "gp07_replay_01_passed": True, "hit_count_mismatch": False}
    if retrieval_replay_omissions_from_twin_diff_v1(ok_twin):
        errors.append("passed_twin_should_emit_no_omissions")
    return _proof_meta("gp07_replay18_twin_failure_emits_rd_replay_twin", errors)


def verify_gp07_replay18_wired_runner_ids_match_static() -> dict[str, Any]:
    errors: list[str] = []
    for gid, fn in _wired_retrieval_gp07_replay_runners_v1().items():
        out = fn()
        if out.get("id") != gid:
            errors.append(f"{gid}_returned_{out.get('id')}")
    return _proof_meta("gp07_replay18_wired_runner_ids_match", errors)


def run_retrieval_gp07_stage_c_replay_gates_v1(
    *,
    abort_on_hard_fail: bool = True,
) -> dict[str, Any]:
    """Execute stage **C** replay gates — delegates to **P07-27** harness."""
    from vector.domains.cortex.retrieval.retrieval_verification_harness import (
        run_retrieval_gp07_stage_c_replay_gates_v1 as _harness_stage_c_v1,
    )

    return _harness_stage_c_v1(abort_on_hard_fail=abort_on_hard_fail)


def run_retrieval_gp07_pr_blocking_static_stages_v1(
    *,
    abort_on_hard_fail: bool = True,
) -> dict[str, Any]:
    """PR-blocking bundle — delegates to **P07-27** harness."""
    from vector.domains.cortex.retrieval.retrieval_verification_harness import (
        run_retrieval_gp07_pr_blocking_static_stages_v1 as _harness_pr_blocking_v1,
    )

    return _harness_pr_blocking_v1(abort_on_hard_fail=abort_on_hard_fail)


def build_retrieval_replay_inspector_catalog_v1(
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Admin replay inspector — identity law + harness stage-C status + twin diff schema."""
    base = _base_retrieval_replay_inspector_catalog_v1(tenant_id=tenant_id)
    stage_c = run_retrieval_gp07_stage_c_replay_gates_v1(abort_on_hard_fail=False)
    return {
        **base,
        "gp07_replay02_gate_id": GP07_REPLAY02_GATE_ID_V1,
        "rd_replay_twin": RETRIEVAL_RD_REPLAY_TWIN_V1,
        "retrieval_replay_equivalence_proofs_runtime_schema_version": (
            PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION
        ),
        "doctrine_anchors": [
            RETRIEVAL_REPLAY_EQUIVALENCE_SPEC_REF_V1,
            RETRIEVAL_REPLAY_EQUIVALENCE_PROOFS_SPEC_REF_V1,
            RETRIEVAL_VERIFICATION_HARNESS_SPEC_REF_V1,
        ],
        "twin_diff_fields": [
            "receipt_digest_a",
            "receipt_digest_b",
            "retrieval_query_replay_identity_a",
            "retrieval_query_replay_identity_b",
            "hit_count_mismatch",
            "ordering_divergence",
            "omission_multiset_delta",
            "gp07_replay_01_passed",
        ],
        "harness": {
            "stage_c_replay_gates": stage_c,
            "golden_case_id": "query/replay_equivalence_double_run_v1",
            "pr_blocking_stages": ["A", "B", "C"],
        },
        "retrieval_replay_equivalence_runtime_schema_version": (
            PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION
        ),
    }
