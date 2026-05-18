"""Phase 08 P08-17 — synthesis replay equivalence proofs harness (**G-P08-REPLAY-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-replay-equivalence-spec.md`` §Twin.
Wires inline ``prove`` double-run, golden harness, and full admin replay explorer.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.normative import PHASE08_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.synthesis_bounded_caps import normalize_synthesis_omission_law_row_v1
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    GP08_REPLAY_01_GATE_ID_V1,
    GP08_REPLAY_02_GATE_ID_V1,
    PHASE08_REPLAY_EQUIVALENCE_SPEC_REF_V1,
    PHASE08_SYNTHESIS_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION,
    SD_REPLAY_TWIN_V1,
    SynthesisReplayEquivalenceError,
    apply_syn_rep02_retrieval_twin_legality_floor_v1,
    build_synthesis_replay_equivalence_twin_diff_v1,
    build_synthesis_replay_explorer_base_v1,
    compare_gp08_replay_01_double_run_v1,
    compute_synthesis_job_replay_identity_v1,
    record_synthesis_replay_divergence_v1,
    synthesis_replay_omissions_from_twin_diff_v1,
    verify_gp08_replay01_canonical_identity_stable_static,
    verify_gp08_replay01_double_run_match_static,
    verify_gp08_replay01_receipt_embed_law_static,
)

PHASE08_SYNTHESIS_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_REPLAY_EQUIVALENCE_PROOFS_SPEC_REF_V1: Final[str] = PHASE08_REPLAY_EQUIVALENCE_SPEC_REF_V1

from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
    load_synthesis_golden_case_v1,
    synthesis_golden_vectors_v1_root,
)

_SYNTHESIS_PROVE_INTENTS_V1: Final[frozenset[str]] = frozenset({"prove"})
_SYNTHESIS_REPLAY_PROOF_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
    {"replay_equivalence_synthesis"},
)


class SynthesisReplayEquivalenceProofsError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def synthesis_inline_twin_required_v1(envelope: Mapping[str, Any]) -> bool:
    intent = str(envelope.get("synthesis_intent") or "").strip().lower()
    wl = str(envelope.get("synthesis_workload_class") or "").strip()
    return intent in _SYNTHESIS_PROVE_INTENTS_V1 or wl in _SYNTHESIS_REPLAY_PROOF_WORKLOADS_V1


def _synthetic_run_from_golden_inputs_v1(
    *,
    envelope: Mapping[str, Any],
    retrieval_subqueries: Sequence[Mapping[str, Any]],
    sd_codes_sorted: Sequence[str],
) -> dict[str, Any]:
    identity = compute_synthesis_job_replay_identity_v1(
        envelope=envelope,
        retrieval_ingress_digest=str(envelope.get("retrieval_ingress_digest") or "b" * 64),
        retrieval_subqueries=retrieval_subqueries,
        sd_codes_sorted=sd_codes_sorted,
    )
    receipt_digest = compute_synthesis_job_replay_identity_v1(
        envelope={"receipt_body": dict(envelope)},
        retrieval_ingress_digest=str(envelope.get("retrieval_ingress_digest") or "b" * 64),
        retrieval_subqueries=retrieval_subqueries,
        sd_codes_sorted=sd_codes_sorted,
    )
    claims = list(envelope.get("claims") or [])
    return {
        PHASE08_REPLAY_IDENTITY_FIELD_V1: identity,
        "synthesis_job_receipt": {
            "receipt_digest": receipt_digest,
            "retrieval_subqueries": [dict(r) for r in retrieval_subqueries if isinstance(r, Mapping)],
        },
        "claims": claims,
        "synthesis_citation_envelope": dict(envelope.get("synthesis_citation_envelope") or {}),
        "synthesis_intelligence_artifact": {
            "artifact_id": str(envelope.get("artifact_id") or "golden-artifact"),
            "artifact_digest": str(envelope.get("artifact_digest") or ""),
            "claims": claims,
            "synthesis_citation_envelope": dict(envelope.get("synthesis_citation_envelope") or {}),
            "synthesis_omission_rows": list(envelope.get("synthesis_omission_rows") or []),
        },
    }


def run_synthesis_golden_replay_equivalence_case_v1(case: Mapping[str, Any]) -> dict[str, Any]:
    """Static golden double-run for ``replay_equivalence/double_run_v1``."""
    inputs = case.get("inputs")
    if not isinstance(inputs, dict):
        raise SynthesisReplayEquivalenceProofsError("golden_case_missing_inputs")
    expected = case.get("expected")
    if not isinstance(expected, dict):
        raise SynthesisReplayEquivalenceProofsError("golden_case_missing_expected")
    envelope = dict(inputs.get("envelope") or {})
    subqueries = list(inputs.get("retrieval_subqueries") or [])
    sd_sorted = list(inputs.get("sd_codes_sorted") or [])
    run_a = _synthetic_run_from_golden_inputs_v1(
        envelope=envelope,
        retrieval_subqueries=subqueries,
        sd_codes_sorted=sd_sorted,
    )
    run_b = _synthetic_run_from_golden_inputs_v1(
        envelope=envelope,
        retrieval_subqueries=subqueries,
        sd_codes_sorted=sd_sorted,
    )
    twin = build_synthesis_replay_equivalence_twin_diff_v1(run_a, run_b)
    try:
        compare_gp08_replay_01_double_run_v1(run_a, run_b)
    except SynthesisReplayEquivalenceError:
        twin["gp08_replay_01_passed"] = False
        twin["gp08_replay_proof_passed"] = False
    if expected.get("gp08_replay_proof_passed") is True and not twin.get("gp08_replay_proof_passed"):
        raise SynthesisReplayEquivalenceProofsError(
            "expected_gp08_replay_proof_pass",
            detail=dict(twin),
        )
    if expected.get("gp08_replay_proof_passed") is False and twin.get("gp08_replay_proof_passed"):
        raise SynthesisReplayEquivalenceProofsError("expected_gp08_replay_proof_fail")
    return {
        "case_id": case.get("case_id"),
        "gate_id": case.get("gate_id"),
        "twin": twin,
        "gp08_replay_proof_passed": bool(twin.get("gp08_replay_proof_passed")),
    }


def execute_synthesis_inline_replay_proof_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    body: Mapping[str, Any],
    job_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """``inline_twin`` — run FSM twice and attach structural twin diff to primary result."""
    from vector.domains.cortex.synthesis.synthesis_orchestrator import (
        execute_synthesis_job_envelope_v1,
    )

    run_a = execute_synthesis_job_envelope_v1(
        session,
        tenant_id=tenant_id,
        body=body,
        job_id=job_id,
        _twin_inner=True,
    )
    run_b = execute_synthesis_job_envelope_v1(
        session,
        tenant_id=tenant_id,
        body=body,
        _twin_inner=True,
    )
    twin = build_synthesis_replay_equivalence_twin_diff_v1(run_a, run_b)
    try:
        compare_gp08_replay_01_double_run_v1(run_a, run_b)
    except SynthesisReplayEquivalenceError:
        if not twin.get("gp08_replay_proof_passed"):
            twin["gp08_replay_01_passed"] = False
            twin["gp08_replay_proof_passed"] = False
        record_synthesis_replay_divergence_v1(
            tenant_id=str(tenant_id),
            synthesis_job_replay_identity_a=str(twin.get("synthesis_job_replay_identity_a") or ""),
            synthesis_job_replay_identity_b=str(twin.get("synthesis_job_replay_identity_b") or ""),
            detail=dict(twin),
        )
    twin_rows: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    if not twin.get("gp08_replay_proof_passed"):
        twin_rows = synthesis_replay_omissions_from_twin_diff_v1(twin)
        normalized = [
            normalize_synthesis_omission_law_row_v1(row) for row in twin_rows if isinstance(row, Mapping)
        ]
        receipt = run_a.get("synthesis_job_receipt")
        if isinstance(receipt, Mapping):
            existing = list(receipt.get("synthesis_omission_rows") or [])
            receipt = dict(receipt)
            receipt["synthesis_omission_rows"] = existing + normalized
            run_a["synthesis_job_receipt"] = receipt
        legality = str(run_a.get("synthesis_legality_class") or "synthesis_replay_safe")
        legality = apply_syn_rep02_retrieval_twin_legality_floor_v1(
            legality,
            gp08_replay_01_passed=bool(twin.get("gp08_replay_01_passed")),
        )
        if twin_rows and legality == "synthesis_replay_safe":
            legality = "synthesis_degraded"
        run_a["synthesis_legality_class"] = legality
    run_a["replay_equivalence_twin"] = twin
    run_a["gp08_replay_proof_passed"] = bool(twin.get("gp08_replay_proof_passed"))
    job_id_a = run_a.get("job_id")
    if job_id_a:
        from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

        job_row = session.get(CortexSynthesisJob, uuid.UUID(str(job_id_a)))
        if job_row is not None:
            receipt_row = dict(job_row.receipt_json or {})
            receipt_row["replay_equivalence_twin"] = twin
            if twin_rows:
                receipt_row["synthesis_omission_rows"] = list(
                    receipt_row.get("synthesis_omission_rows") or [],
                ) + normalized
            job_row.receipt_json = receipt_row
            job_row.synthesis_legality_class = str(run_a.get("synthesis_legality_class") or "")
            session.flush()
    return run_a


def run_operator_replay_prove_on_job_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> dict[str, Any]:
    """``operator_twin`` — re-run envelope from a completed job and compare to stored receipt."""
    from vector.domains.cortex.synthesis.synthesis_orchestrator import (
        execute_synthesis_job_envelope_v1,
        get_synthesis_job_detail_v1,
    )

    detail = get_synthesis_job_detail_v1(session, tenant_id=tenant_id, job_id=job_id)
    if detail.get("status") != "completed":
        raise SynthesisReplayEquivalenceProofsError(
            "synthesis_job_not_completed",
            detail={"status": detail.get("status")},
        )
    envelope = dict(detail.get("envelope_json") or {})
    envelope["synthesis_intent"] = "prove"
    stored = {
        PHASE08_REPLAY_IDENTITY_FIELD_V1: detail.get("synthesis_job_replay_identity") or "",
        "synthesis_job_receipt": dict(detail.get("synthesis_job_receipt") or {}),
        "synthesis_legality_class": detail.get("synthesis_legality_class"),
        "artifact_id": (detail.get("synthesis_job_receipt") or {}).get("artifact_id"),
        "artifact_digest": (detail.get("synthesis_job_receipt") or {}).get("artifact_digest"),
        "claims": list((detail.get("synthesis_job_receipt") or {}).get("claims") or []),
        "synthesis_citation_envelope": dict(
            (detail.get("synthesis_job_receipt") or {}).get("synthesis_citation_envelope") or {},
        ),
    }
    replay_run = execute_synthesis_job_envelope_v1(
        session,
        tenant_id=tenant_id,
        body=envelope,
        _twin_inner=True,
    )
    twin = build_synthesis_replay_equivalence_twin_diff_v1(stored, replay_run)
    twin["structural_twin_mode"] = "operator_twin"
    twin["reference_job_id"] = str(job_id)
    return {
        "surface_kind": "synthesis_operator_replay_prove",
        "tenant_id": str(tenant_id),
        "job_id": str(job_id),
        "gate_id": GP08_REPLAY_01_GATE_ID_V1,
        "gp08_replay_proof_passed": bool(twin.get("gp08_replay_proof_passed")),
        "replay_equivalence_twin": twin,
        "stored_synthesis_job_replay_identity": stored.get(PHASE08_REPLAY_IDENTITY_FIELD_V1),
        "replay_synthesis_job_replay_identity": replay_run.get(PHASE08_REPLAY_IDENTITY_FIELD_V1),
    }


def _proof_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_REPLAY_01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase08_synthesis_replay_equivalence_proofs_runtime_schema_version": (
                PHASE08_SYNTHESIS_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp08_replay17_golden_double_run_corpus_static() -> dict[str, Any]:
    errors: list[str] = []
    case_id = "replay_equivalence/double_run_v1"
    try:
        case = load_synthesis_golden_case_v1(case_id)
        a = run_synthesis_golden_replay_equivalence_case_v1(case)
        b = run_synthesis_golden_replay_equivalence_case_v1(case)
        if a.get("gp08_replay_proof_passed") != b.get("gp08_replay_proof_passed"):
            errors.append("determinism_replay_failed")
    except (SynthesisReplayEquivalenceProofsError, FileNotFoundError) as exc:
        errors.append(f"{case_id}:{exc}")
    return _proof_meta("gp08_replay17_golden_double_run_corpus", errors)


def verify_gp08_replay17_twin_failure_emits_sd_replay_twin_static() -> dict[str, Any]:
    errors: list[str] = []
    twin = {
        "gp08_replay_01_passed": False,
        "structural_twin_passed": False,
        "gp08_replay_proof_passed": False,
        "receipt_digest_a": "a" * 64,
        "receipt_digest_b": "b" * 64,
    }
    rows = synthesis_replay_omissions_from_twin_diff_v1(twin)
    if not rows or rows[0].get("sd_code") != SD_REPLAY_TWIN_V1:
        errors.append("expected_sd_replay_twin")
    ok = {**twin, "gp08_replay_proof_passed": True, "structural_twin_passed": True, "gp08_replay_01_passed": True}
    if synthesis_replay_omissions_from_twin_diff_v1(ok):
        errors.append("passed_twin_should_emit_no_omissions")
    return _proof_meta("gp08_replay17_twin_failure_emits_sd_replay_twin", errors)


def verify_gp08_replay17_structural_twin_law_static() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
        compare_synthesis_structural_artifact_twin_v1,
    )

    base_claims = [{"claim_kind": "observation", "citations": ["c1"]}]
    art_a = {
        "claims": base_claims,
        "synthesis_citation_envelope": {
            "citations": [{"citation_id": "c1", "hit_digest": "h1"}],
        },
        "synthesis_omission_rows": [],
    }
    art_b = {
        "claims": base_claims,
        "synthesis_citation_envelope": {
            "citations": [{"citation_id": "c1", "hit_digest": "h1"}],
        },
        "synthesis_omission_rows": [],
    }
    ok = compare_synthesis_structural_artifact_twin_v1(art_a, art_b)
    if not ok.get("structural_twin_passed"):
        errors.append("identical_structural_should_pass")
    art_c = {**art_b, "claims": [{"claim_kind": "hypothesis", "citations": []}]}
    bad = compare_synthesis_structural_artifact_twin_v1(art_a, art_c)
    if bad.get("structural_twin_passed"):
        errors.append("claim_kind_mismatch_should_fail")
    return _proof_meta("gp08_replay17_structural_twin_law", errors)


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


def _run_gp08_replay01_bundle_static() -> dict[str, Any]:
    return _compose_gate_results_v1(
        GP08_REPLAY_01_GATE_ID_V1,
        "synthesis_replay_01_double_run_and_identity",
        [
            verify_gp08_replay01_canonical_identity_stable_static(),
            verify_gp08_replay01_double_run_match_static(),
            verify_gp08_replay01_receipt_embed_law_static(),
            verify_gp08_replay17_golden_double_run_corpus_static(),
            verify_gp08_replay17_twin_failure_emits_sd_replay_twin_static(),
            verify_gp08_replay17_structural_twin_law_static(),
        ],
    )


def run_synthesis_gp08_replay_proof_harness_v1() -> dict[str, Any]:
    """CI harness — static **G-P08-REPLAY-01** bundle for synthesis replay proofs."""
    result = _run_gp08_replay01_bundle_static()
    return {
        "passed": bool(result.get("passed")),
        "gate_id": GP08_REPLAY_01_GATE_ID_V1,
        "results": [result],
    }


def build_synthesis_replay_explorer_catalog_v1(
    *,
    tenant_id: str | None = None,
    recent_jobs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Full admin replay explorer — pin law, harness status, twin diff schema (Step **17**)."""
    base = build_synthesis_replay_explorer_base_v1(
        tenant_id=tenant_id,
        recent_jobs=recent_jobs,
    )
    harness = run_synthesis_gp08_replay_proof_harness_v1()
    return {
        **base,
        "phase08_synthesis_replay_equivalence_proofs_runtime_schema_version": (
            PHASE08_SYNTHESIS_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION
        ),
        "sd_replay_twin": SD_REPLAY_TWIN_V1,
        "doctrine_anchors": [
            SYNTHESIS_REPLAY_EQUIVALENCE_PROOFS_SPEC_REF_V1,
        ],
        "twin_diff_fields": [
            "receipt_digest_a",
            "receipt_digest_b",
            "synthesis_job_replay_identity_a",
            "synthesis_job_replay_identity_b",
            "artifact_digest_a",
            "artifact_digest_b",
            "claim_kind_sequence_match",
            "citation_set_match",
            "sd_multiset_match",
            "structural_twin_passed",
            "gp08_replay_01_passed",
            "gp08_replay_proof_passed",
            "wording_diff_only",
        ],
        "harness": {
            "gp08_replay_proof_harness": harness,
            "golden_case_id": "replay_equivalence/double_run_v1",
            "inline_twin_intents": sorted(_SYNTHESIS_PROVE_INTENTS_V1),
            "inline_twin_workloads": sorted(_SYNTHESIS_REPLAY_PROOF_WORKLOADS_V1),
        },
        "operator_replay_prove_route": (
            "/admin/tenants/{tenant_id}/cortex/synthesis/jobs/{job_id}/replay-prove"
        ),
        "gp08_replay_02_gate_id": GP08_REPLAY_02_GATE_ID_V1,
    }
