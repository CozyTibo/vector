"""Phase 08 P08-28 — synthesis evaluation harness (**G-P08-EVAL-01/02**).

Normative: ``DOCS/cortex/synthesis/phase-08-evaluation-quality-governance.md``.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
    compute_synthesis_artifact_digest_v1,
    list_synthesis_intelligence_artifact_validation_errors_v1,
    validate_synthesis_intelligence_artifact_v1,
)
from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
    bind_synthesis_golden_corpus_at_root_v1,
    load_synthesis_corpus_manifest_v1,
    load_synthesis_golden_case_v1,
    run_synthesis_golden_case_v1,
    synthesis_golden_vectors_v1_root,
)
from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    map_retrieval_legality_to_synthesis_floor_v1,
    _legality_ordinal,
)
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1
from vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs import (
    run_synthesis_gp08_replay_proof_harness_v1,
)
from vector.domains.cortex.synthesis.synthesis_tenant_verification import (
    verify_tenant_synthesis_slice_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

PHASE08_SYNTHESIS_EVALUATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_EVALUATION_CONTRACT_V1: Final[str] = "synthesis_evaluation_receipt_v1"

SYNTHESIS_EVALUATION_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-evaluation-quality-governance.md"
)

GP08_EVAL01_GATE_ID_V1: Final[str] = "G-P08-EVAL-01"

GP08_EVAL02_GATE_ID_V1: Final[str] = "G-P08-EVAL-02"

SYNTHESIS_EVALUATION_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/synthesis/evaluation",
    "/admin/catalog/cortex/synthesis/evaluation",
)

EvaluationGateSeverityV1 = Literal["hard_fail", "warn"]

_EVAL_RUN_LEDGER_MAX_V1: Final[int] = 32
_eval_run_ledger_v1: list[dict[str, Any]] = []


class SynthesisEvaluationError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def record_synthesis_evaluation_run_v1(receipt: dict[str, Any]) -> dict[str, Any]:
    """Append evaluation receipt to in-process run ledger (newest last)."""
    entry = {
        **receipt,
        "evaluation_run_id": str(uuid.uuid4()),
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    _eval_run_ledger_v1.append(entry)
    while len(_eval_run_ledger_v1) > _EVAL_RUN_LEDGER_MAX_V1:
        _eval_run_ledger_v1.pop(0)
    return entry


def list_synthesis_evaluation_run_ledger_v1() -> list[dict[str, Any]]:
    return list(_eval_run_ledger_v1)


def min_citation_coverage_threshold_v1(*, pack: Mapping[str, Any] | None = None) -> float:
    body = dict(pack or load_synthesis_policy_pack_v1())
    raw = body.get("min_citation_coverage", 0.95)
    return float(raw)


def compute_citation_coverage_metrics_v1(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """``cited_claims / total_claims`` for non-discourse substantive claims."""
    claims = [c for c in (artifact.get("claims") or []) if isinstance(c, Mapping)]
    substantive = [c for c in claims if not c.get("discourse_only")]
    total_claims = len(substantive)
    cited_claims = sum(
        1
        for c in substantive
        if not c.get("omitted_reason")
        and isinstance(c.get("citations"), list)
        and len(c.get("citations") or []) > 0
    )
    omitted_claims = [c for c in substantive if c.get("omitted_reason")]
    omission_complete = all(
        bool(str(c.get("omitted_reason") or "").startswith("SD-")) for c in omitted_claims
    )
    coverage_ratio = (cited_claims / total_claims) if total_claims else 1.0
    return {
        "total_claims": total_claims,
        "cited_claims": cited_claims,
        "omitted_claims": len(omitted_claims),
        "coverage_ratio": coverage_ratio,
        "omission_completeness_passed": omission_complete if omitted_claims else True,
    }


def evaluate_upstream_legality_fidelity_v1(artifact: Mapping[str, Any]) -> bool:
    """No illegal legality upgrade vs pinned upstream retrieval class."""
    posture = artifact.get("synthesis_legality_posture")
    if not isinstance(posture, Mapping):
        return True
    upstream = str(posture.get("upstream_retrieval_legality_class") or "retrieval_partial").strip().lower()
    synth = str(artifact.get("synthesis_legality_class") or "synthesis_partial").strip().lower()
    if "forbidden" in upstream and synth != "synthesis_forbidden":
        return False
    if "unverifiable" in upstream and synth == "synthesis_replay_safe":
        return False
    floor = map_retrieval_legality_to_synthesis_floor_v1(upstream)
    return _legality_ordinal(synth) <= _legality_ordinal(floor)


def evaluate_caps_respect_v1(artifact: Mapping[str, Any]) -> bool:
    """No silent truncation — cap SD codes must appear in omission rows when present."""
    rows = [r for r in (artifact.get("synthesis_omission_rows") or []) if isinstance(r, Mapping)]
    cap_codes = {str(r.get("sd_code") or "") for r in rows if str(r.get("sd_code", "")).startswith("SD-CAP-")}
    rollup = artifact.get("synthesis_degradation_rollup")
    if not isinstance(rollup, Mapping):
        return len(cap_codes) == 0
    rollup_codes = {
        str(k)
        for k, v in rollup.items()
        if str(k).startswith("SD-CAP-") and int(v or 0) > 0
    }
    return cap_codes == rollup_codes or not rollup_codes


def _golden_case_passed_v1(result: Mapping[str, Any]) -> bool:
    if "gp08_replay_proof_passed" in result:
        return bool(result["gp08_replay_proof_passed"])
    if result.get("synthesis_legality_class"):
        return True
    return bool(result.get("synthesis_workload_class"))


def build_sample_artifact_from_golden_replay_case_v1() -> dict[str, Any]:
    """Synthetic artifact body from golden replay case (CI / static eval)."""
    case = load_synthesis_golden_case_v1("replay_equivalence/double_run_v1")
    inputs = case.get("inputs") or {}
    envelope = dict(inputs.get("envelope") or {})
    claims = list(envelope.get("claims") or [])
    body: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": "eval-sample-artifact",
        "artifact_kind": "degradation_brief",
        "synthesis_legality_class": "synthesis_replay_safe",
        "synthesis_job_replay_identity": "d" * 64,
        "retrieval_query_replay_identity": "c" * 64,
        "synthesis_policy_pack_digest": "f" * 64,
        "synthesis_publication_epoch": None,
        "evidence_scope_summary": {"scope_count": 1},
        "claims": claims,
        "synthesis_citation_envelope": dict(envelope.get("synthesis_citation_envelope") or {}),
        "synthesis_omission_rows": list(envelope.get("synthesis_omission_rows") or []),
        "synthesis_degradation_rollup": {"sd_code_counts": {}},
        "synthesis_legality_posture": {
            "upstream_retrieval_legality_class": "retrieval_replay_safe",
            "synthesis_legality_class": "synthesis_replay_safe",
        },
        "lineage_chain_digest": None,
        "llm_trace_refs": [],
        "retrieval_receipt_embed": {},
        "non_authoritative": False,
    }
    body["artifact_digest"] = compute_synthesis_artifact_digest_v1(body)
    return body


def evaluate_gp08_eval01_citation_coverage_v1(
    artifact: Mapping[str, Any],
    *,
    pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """**G-P08-EVAL-01** — citation coverage ≥ policy ``min_citation_coverage``."""
    metrics = compute_citation_coverage_metrics_v1(artifact)
    threshold = min_citation_coverage_threshold_v1(pack=pack)
    passed = float(metrics["coverage_ratio"]) >= threshold
    return {
        "id": GP08_EVAL01_GATE_ID_V1,
        "name": "gp08_eval01_citation_coverage",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            **metrics,
            "min_citation_coverage_threshold": threshold,
        },
    }


def evaluate_gp08_eval02_wording_drift_v1(
    *,
    wording_diff_detected: bool = False,
) -> dict[str, Any]:
    """**G-P08-EVAL-02** — wording drift tracked; never blocks certification."""
    return {
        "id": GP08_EVAL02_GATE_ID_V1,
        "name": "gp08_eval02_wording_drift",
        "passed": True,
        "severity": "warn",
        "detail": {
            "wording_diff_detected": wording_diff_detected,
            "blocking": False,
            "note": "structural replay (G-P08-REPLAY-01) is authoritative; wording is diagnostic only",
        },
    }


def run_golden_corpus_evaluation_v1() -> dict[str, Any]:
    """Run all golden cases; aggregate per-case gate outcomes (no DB)."""
    manifest = load_synthesis_corpus_manifest_v1()
    case_rows: list[dict[str, Any]] = []
    all_passed = True
    for row in manifest.get("cases") or []:
        if not isinstance(row, Mapping):
            continue
        case_id = str(row["case_id"])
        try:
            result = run_synthesis_golden_case_v1(load_synthesis_golden_case_v1(case_id))
            passed = _golden_case_passed_v1(result)
        except Exception as exc:
            passed = False
            result = {"error": str(exc)}
        all_passed = all_passed and passed
        case_rows.append(
            {
                "case_id": case_id,
                "gate_id": row.get("gate_id"),
                "passed": passed,
                "result": result,
            },
        )
    return {
        "golden_corpus_passed": all_passed,
        "case_count": len(case_rows),
        "cases": case_rows,
        "corpus_id": manifest.get("corpus_id"),
    }


def _evaluate_artifact_quality_dimensions_v1(
    artifact: Mapping[str, Any],
    *,
    wording_diff_detected: bool = False,
) -> dict[str, Any]:
    eval01 = evaluate_gp08_eval01_citation_coverage_v1(artifact)
    eval02 = evaluate_gp08_eval02_wording_drift_v1(wording_diff_detected=wording_diff_detected)
    schema_errors = list_synthesis_intelligence_artifact_validation_errors_v1(artifact)
    try:
        validate_synthesis_intelligence_artifact_v1(artifact)
        schema_passed = len(schema_errors) == 0
    except Exception:
        schema_passed = False
    replay_harness = run_synthesis_gp08_replay_proof_harness_v1()
    dimensions = {
        "citation_coverage": eval01,
        "wording_drift": eval02,
        "structural_replay": {
            "id": "G-P08-REPLAY-01",
            "passed": bool(replay_harness.get("passed")),
            "severity": "hard_fail",
            "detail": replay_harness,
        },
        "omission_completeness": {
            "id": "omission_completeness",
            "passed": bool(
                compute_citation_coverage_metrics_v1(artifact).get("omission_completeness_passed"),
            ),
            "severity": "hard_fail",
            "detail": compute_citation_coverage_metrics_v1(artifact),
        },
        "upstream_fidelity": {
            "id": "upstream_fidelity",
            "passed": evaluate_upstream_legality_fidelity_v1(artifact),
            "severity": "hard_fail",
            "detail": {},
        },
        "schema_validity": {
            "id": "schema_validity",
            "passed": schema_passed,
            "severity": "hard_fail",
            "detail": {"errors": schema_errors},
        },
        "caps_respect": {
            "id": "caps_respect",
            "passed": evaluate_caps_respect_v1(artifact),
            "severity": "hard_fail",
            "detail": {},
        },
    }
    hard_passed = all(
        d.get("passed")
        for d in dimensions.values()
        if d.get("severity") == "hard_fail"
    )
    return {
        "dimensions": dimensions,
        "evaluation_passed": hard_passed,
    }


def run_synthesis_evaluation_suite_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID | None = None,
    record_ledger: bool = True,
) -> dict[str, Any]:
    """Run golden corpus + optional tenant-scoped probes; emit ``evaluation_receipt``."""
    golden = run_golden_corpus_evaluation_v1()
    sample = build_sample_artifact_from_golden_replay_case_v1()
    quality = _evaluate_artifact_quality_dimensions_v1(sample, wording_diff_detected=False)
    tenant_block: dict[str, Any] | None = None
    if session is not None and tenant_id is not None:
        latest_artifact = session.scalar(
            select(CortexSynthesisArtifact)
            .where(CortexSynthesisArtifact.tenant_id == tenant_id)
            .order_by(CortexSynthesisArtifact.created_at.desc())
            .limit(1),
        )
        if latest_artifact is not None and isinstance(latest_artifact.body_json, Mapping):
            body = dict(latest_artifact.body_json)
            quality = _evaluate_artifact_quality_dimensions_v1(
                body,
                wording_diff_detected=False,
            )
        completed_jobs = len(
            list(
                session.scalars(
                    select(CortexSynthesisJob).where(
                        CortexSynthesisJob.tenant_id == tenant_id,
                        CortexSynthesisJob.status == "completed",
                    ),
                ).all(),
            ),
        )
        tver = verify_tenant_synthesis_slice_v1(session, tenant_id=tenant_id)
        tenant_block = {
            "tenant_id": str(tenant_id),
            "completed_jobs_count": completed_jobs,
            "latest_artifact_id": str(latest_artifact.id) if latest_artifact else None,
            "tenant_verification": tver,
        }
    receipt = {
        "surface_kind": "verification_probe",
        "synthesis_evaluation_contract": SYNTHESIS_EVALUATION_CONTRACT_V1,
        "synthesis_evaluation_runtime_schema_version": (
            PHASE08_SYNTHESIS_EVALUATION_RUNTIME_SCHEMA_VERSION
        ),
        "spec_ref": SYNTHESIS_EVALUATION_SPEC_REF_V1,
        "evaluation_passed": bool(golden.get("golden_corpus_passed"))
        and bool(quality.get("evaluation_passed")),
        "golden_corpus": golden,
        "quality_dimensions": quality.get("dimensions"),
        "metrics_table": {
            "citation_coverage": quality["dimensions"]["citation_coverage"]["detail"],
            "golden_case_count": golden.get("case_count"),
        },
        "gate_results": {
            GP08_EVAL01_GATE_ID_V1: quality["dimensions"]["citation_coverage"],
            GP08_EVAL02_GATE_ID_V1: quality["dimensions"]["wording_drift"],
            "G-P08-REPLAY-01": quality["dimensions"]["structural_replay"],
        },
        "tenant": tenant_block,
        "sample_artifact_evaluated": True,
    }
    if record_ledger:
        record_synthesis_evaluation_run_v1(receipt)
    return receipt


def build_synthesis_evaluation_explorer_v1(
    session: Session | None = None,
    *,
    tenant_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Admin evaluation explorer — latest receipt + ledger tail."""
    receipt = run_synthesis_evaluation_suite_v1(
        session,
        tenant_id=tenant_id,
        record_ledger=False,
    )
    return {
        **receipt,
        "evaluation_run_ledger_tail": list_synthesis_evaluation_run_ledger_v1()[-5:],
        "golden_vectors_root": str(synthesis_golden_vectors_v1_root()),
    }


def build_synthesis_evaluation_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for evaluation gates (no tenant DB required)."""
    bind = bind_synthesis_golden_corpus_at_root_v1()
    sample = build_sample_artifact_from_golden_replay_case_v1()
    eval01 = evaluate_gp08_eval01_citation_coverage_v1(sample)
    eval02 = evaluate_gp08_eval02_wording_drift_v1()
    return {
        "surface_kind": "verification_probe",
        "spec_ref": SYNTHESIS_EVALUATION_SPEC_REF_V1,
        "synthesis_evaluation_contract": SYNTHESIS_EVALUATION_CONTRACT_V1,
        "gate_ids": [GP08_EVAL01_GATE_ID_V1, GP08_EVAL02_GATE_ID_V1],
        "min_citation_coverage_default": min_citation_coverage_threshold_v1(),
        "golden_corpus_bind": bind,
        "static_gate_samples": {"G-P08-EVAL-01": eval01, "G-P08-EVAL-02": eval02},
    }


def _eval_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": "P08-28-eval",
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase08_synthesis_evaluation_runtime_schema_version": (
                PHASE08_SYNTHESIS_EVALUATION_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp08_eval01_citation_coverage_static() -> dict[str, Any]:
    sample = build_sample_artifact_from_golden_replay_case_v1()
    out = evaluate_gp08_eval01_citation_coverage_v1(sample)
    return out if out.get("id") == GP08_EVAL01_GATE_ID_V1 else _eval_meta("gp08_eval01_wrong_id", ["id"])


def verify_gp08_eval02_wording_drift_non_blocking_static() -> dict[str, Any]:
    out = evaluate_gp08_eval02_wording_drift_v1(wording_diff_detected=True)
    errors: list[str] = []
    if not out.get("passed"):
        errors.append("eval02_must_always_pass")
    if out.get("severity") != "warn":
        errors.append("eval02_must_be_warn")
    if out.get("detail", {}).get("blocking"):
        errors.append("eval02_must_not_block")
    return out if not errors else _eval_meta("gp08_eval02_non_blocking", errors)


def verify_gp08_eval03_golden_corpus_suite_static() -> dict[str, Any]:
    errors: list[str] = []
    golden = run_golden_corpus_evaluation_v1()
    if not golden.get("golden_corpus_passed"):
        errors.append("golden_corpus_failed")
    if int(golden.get("case_count") or 0) < 4:
        errors.append("golden_case_count_low")
    return _eval_meta("gp08_eval03_golden_corpus_suite", errors)


def verify_gp08_eval04_evaluation_suite_sample_static() -> dict[str, Any]:
    errors: list[str] = []
    receipt = run_synthesis_evaluation_suite_v1(None, tenant_id=None, record_ledger=False)
    if not receipt.get("evaluation_passed"):
        errors.append("evaluation_suite_failed")
    if receipt.get("surface_kind") != "verification_probe":
        errors.append("surface_kind_mismatch")
    return _eval_meta("gp08_eval04_evaluation_suite_sample", errors)


def verify_gp08_eval05_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = (
        "/admin/tenants/{tenant_id}/cortex/synthesis/evaluation",
        "/admin/catalog/cortex/synthesis/evaluation",
    )
    if SYNTHESIS_EVALUATION_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    return _eval_meta("gp08_eval05_admin_openapi_path_matrix", errors)


def verify_gp08_eval01_synthesis_evaluation_static_bundle() -> dict[str, Any]:
    """**G-P08-EVAL-01** bundle — static evaluation harness closure."""
    errors: list[str] = []
    for fn in (
        verify_gp08_eval01_citation_coverage_static,
        verify_gp08_eval02_wording_drift_non_blocking_static,
        verify_gp08_eval03_golden_corpus_suite_static,
        verify_gp08_eval04_evaluation_suite_sample_static,
        verify_gp08_eval05_admin_openapi_path_matrix_static,
    ):
        out = fn()
        if not out.get("passed"):
            errors.append(str(out.get("name")))
    return _eval_meta("gp08_eval01_synthesis_evaluation_static_bundle", errors)
