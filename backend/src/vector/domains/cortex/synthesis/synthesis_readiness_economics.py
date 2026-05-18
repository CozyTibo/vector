"""Phase 08 P08-24 — Synthesis readiness + economics probes (mirror **P05/06/07**).

Normative: ``DOCS/cortex/synthesis/phase-08-evaluation-quality-governance.md`` §6.
**G-P08-ECO-01..03** — derived_aggregate cost proxies (not billing truth).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from typing import Any, Final, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_synthesized_scopes_v1,
)
from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
    synthesis_golden_corpus_case_count_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

SYNTHESIS_READINESS_ECONOMICS_SCHEMA_VERSION: Final[int] = 1
SYNTHESIS_READINESS_ECONOMICS_CONTRACT_V1: Final[str] = "synthesis_readiness_economics_v1"
SYNTHESIS_ECONOMICS_THRESHOLD_TABLE_VERSION_V1: Final[int] = 1

GP08_ECO01_GATE_ID_V1: Final[str] = "G-P08-ECO-01"
GP08_ECO02_GATE_ID_V1: Final[str] = "G-P08-ECO-02"
GP08_ECO03_GATE_ID_V1: Final[str] = "G-P08-ECO-03"

SYNTHESIS_READINESS_ECONOMICS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-evaluation-quality-governance.md"
)

SYNTHESIS_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/synthesis/readiness-economics",
)

ProbeProfileV1 = Literal["clean", "hostile"]

_COST_BAND_LOW_MAX_V1: Final[int] = 5_000
_COST_BAND_MEDIUM_MAX_V1: Final[int] = 50_000


def _golden_case_count_v1() -> int:
    return synthesis_golden_corpus_case_count_v1()


def _threshold_max_cases_for_profile_v1(profile: ProbeProfileV1) -> int:
    return 0 if profile == "hostile" else 64


def _threshold_max_avg_job_duration_ms_v1(profile: ProbeProfileV1) -> int:
    return 0 if profile == "hostile" else 3_600_000


def estimated_monthly_cost_band_v1(cost_score: int) -> str:
    """Catalog band from integer cost proxy (not billing truth)."""
    if cost_score < _COST_BAND_LOW_MAX_V1:
        return "low"
    if cost_score < _COST_BAND_MEDIUM_MAX_V1:
        return "medium"
    return "high"


def _job_duration_ms_v1(job: CortexSynthesisJob) -> int:
    if job.started_at and job.completed_at:
        delta = job.completed_at - job.started_at
        return max(0, int(delta.total_seconds() * 1000))
    receipt = dict(job.receipt_json or {})
    trace = receipt.get("synthesis_job_log") or {}
    if isinstance(trace, dict) and trace.get("duration_ms") is not None:
        return max(0, int(trace["duration_ms"]))
    return 0


def _job_llm_tokens_v1(job: CortexSynthesisJob) -> int:
    receipt = dict(job.receipt_json or {})
    llm = receipt.get("llm") or {}
    if isinstance(llm, dict) and llm.get("tokens_used_total") is not None:
        return max(0, int(llm["tokens_used_total"]))
    trace = list(job.execution_trace_json or [])
    for phase in reversed(trace):
        if isinstance(phase, dict) and phase.get("phase") == "LLM":
            return max(0, int(phase.get("tokens_used_total") or 0))
    return 0


def _tenant_economics_probes_v1(session: Session | None, *, tenant_id: uuid.UUID) -> dict[str, int]:
    if session is None:
        return {
            "avg_job_duration_ms": 0,
            "avg_llm_tokens_per_artifact": 0,
            "artifacts_per_index_epoch": 0,
            "completed_jobs_count": 0,
            "artifact_count": 0,
        }
    tid = tenant_id
    completed_jobs = list(
        session.scalars(
            select(CortexSynthesisJob).where(
                CortexSynthesisJob.tenant_id == tid,
                CortexSynthesisJob.status == "completed",
            )
        ).all()
    )
    durations = [_job_duration_ms_v1(j) for j in completed_jobs]
    tokens = [_job_llm_tokens_v1(j) for j in completed_jobs]
    avg_duration = int(sum(durations) / len(durations)) if durations else 0
    avg_tokens_job = int(sum(tokens) / len(tokens)) if tokens else 0

    published = get_published_index_epoch_v1(session, tenant_id=tid)
    artifact_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisArtifact)
            .where(CortexSynthesisArtifact.tenant_id == tid)
        )
        or 0
    )
    per_epoch = 0
    if published:
        per_epoch = int(
            session.scalar(
                select(func.count())
                .select_from(CortexSynthesisArtifact)
                .where(
                    CortexSynthesisArtifact.tenant_id == tid,
                    CortexSynthesisArtifact.synthesis_publication_epoch == published,
                )
            )
            or 0
        )
    scope = count_synthesis_synthesized_scopes_v1(session, tenant_id=tid)
    artifact_total = int(scope.get("artifact_total", 0)) or artifact_count
    total_tokens = sum(tokens)
    avg_tokens_per_artifact = (
        int(total_tokens / max(artifact_total, 1)) if artifact_total > 0 else 0
    )

    return {
        "avg_job_duration_ms": avg_duration,
        "avg_llm_tokens_per_artifact": avg_tokens_per_artifact,
        "artifacts_per_index_epoch": per_epoch,
        "completed_jobs_count": len(completed_jobs),
        "artifact_count": artifact_total,
        "avg_llm_tokens_per_job": avg_tokens_job,
    }


def compute_synthesis_economics_receipt_hash_v1(stats: Mapping[str, int]) -> str:
    payload = json.dumps(dict(sorted(stats.items())), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def build_synthesis_readiness_economics_receipt_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID | str,
    profile: ProbeProfileV1 = "clean",
) -> dict[str, Any]:
    """Numeric readiness / economics receipt (**derived_aggregate**, read-only probes)."""
    tid_uuid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    tid = str(tid_uuid)
    probes = _tenant_economics_probes_v1(session, tenant_id=tid_uuid)
    case_count = int(_golden_case_count_v1())
    max_cases = _threshold_max_cases_for_profile_v1(profile)
    max_duration = _threshold_max_avg_job_duration_ms_v1(profile)

    violations: list[str] = []
    if case_count > max_cases:
        violations.append("SYNTHESIS_ECO_GOLDEN_CASE_BUDGET")
    if (
        probes["completed_jobs_count"] > 0
        and probes["avg_job_duration_ms"] > max_duration
    ):
        violations.append("SYNTHESIS_ECO_JOB_DURATION_BUDGET")

    cost_score = (
        probes["avg_job_duration_ms"] * max(probes["completed_jobs_count"], 1)
        + probes["avg_llm_tokens_per_artifact"] * max(probes["artifact_count"], 1)
    )
    band = estimated_monthly_cost_band_v1(cost_score)

    violations_sorted = sorted(violations)
    stats: dict[str, int] = {
        "avg_job_duration_ms": int(probes["avg_job_duration_ms"]),
        "avg_llm_tokens_per_artifact": int(probes["avg_llm_tokens_per_artifact"]),
        "artifacts_per_index_epoch": int(probes["artifacts_per_index_epoch"]),
        "completed_jobs_count": int(probes["completed_jobs_count"]),
        "golden_corpus_case_count": case_count,
        "synthesis_economics_cost_score": int(cost_score),
        "synthesis_economics_threshold_max_cases": max_cases,
        "synthesis_economics_threshold_max_avg_job_duration_ms": max_duration,
        "synthesis_economics_threshold_table_version": (
            SYNTHESIS_ECONOMICS_THRESHOLD_TABLE_VERSION_V1
        ),
        "synthesis_eco_violation_count": len(violations_sorted),
    }
    receipt_hash = compute_synthesis_economics_receipt_hash_v1(stats)
    return {
        "surface_kind": "derived_aggregate",
        "economics_receipt_hash": receipt_hash,
        "economics_stats": dict(sorted(stats.items())),
        "economics_violations": violations_sorted,
        "estimated_monthly_cost_band": band,
        "probe_profile": profile,
        "synthesis_readiness_economics_contract": SYNTHESIS_READINESS_ECONOMICS_CONTRACT_V1,
        "synthesis_readiness_economics_schema_version": SYNTHESIS_READINESS_ECONOMICS_SCHEMA_VERSION,
        "spec_ref": SYNTHESIS_READINESS_ECONOMICS_SPEC_REF_V1,
        "tenant_id": tid,
    }


def verify_synthesis_readiness_economics_receipt_v1_shape(doc: Mapping[str, Any]) -> list[str]:
    errs: list[str] = []
    if doc.get("synthesis_readiness_economics_contract") != SYNTHESIS_READINESS_ECONOMICS_CONTRACT_V1:
        errs.append("contract_mismatch")
    if doc.get("synthesis_readiness_economics_schema_version") != (
        SYNTHESIS_READINESS_ECONOMICS_SCHEMA_VERSION
    ):
        errs.append("schema_version_mismatch")
    if not isinstance(doc.get("economics_receipt_hash"), str):
        errs.append("missing_receipt_hash")
    if doc.get("surface_kind") != "derived_aggregate":
        errs.append("surface_kind_mismatch")
    band = doc.get("estimated_monthly_cost_band")
    if band not in ("low", "medium", "high"):
        errs.append("invalid_cost_band")
    return errs


def _eco_gate(gate_id: str, name: str, passed: bool, detail: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": passed,
        "severity": "hard_fail",
        "detail": dict(detail),
    }


def verify_gp08_eco01_readiness_economics_clean_profile_static() -> dict[str, Any]:
    """**G-P08-ECO-01** — clean profile admits shipped golden corpus + duration thresholds."""
    body = build_synthesis_readiness_economics_receipt_v1(
        None,
        tenant_id=uuid.UUID(int=0),
        profile="clean",
    )
    shape_errs = verify_synthesis_readiness_economics_receipt_v1_shape(body)
    passed = body.get("economics_violations") == [] and not shape_errs
    return _eco_gate(
        GP08_ECO01_GATE_ID_V1,
        "synthesis_readiness_economics_clean_profile",
        passed,
        {"underlying": body, "shape_errors": shape_errs},
    )


def verify_gp08_eco02_readiness_economics_hostile_profile_static() -> dict[str, Any]:
    """**G-P08-ECO-02** — hostile profile forces golden budget violation when corpus non-empty."""
    body = build_synthesis_readiness_economics_receipt_v1(
        None,
        tenant_id=uuid.UUID(int=0),
        profile="hostile",
    )
    want = ["SYNTHESIS_ECO_GOLDEN_CASE_BUDGET"]
    passed = body.get("economics_violations") == want
    return _eco_gate(
        GP08_ECO02_GATE_ID_V1,
        "synthesis_readiness_economics_hostile_profile",
        passed,
        {"underlying": body},
    )


def verify_gp08_eco03_admin_openapi_path_matrix_static() -> dict[str, Any]:
    """**G-P08-ECO-03** — readiness economics admin OpenAPI path matrix."""
    errors: list[str] = []
    if len(SYNTHESIS_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1) != 1:
        errors.append("path_count")
    for p in SYNTHESIS_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1:
        if "readiness-economics" not in p:
            errors.append(f"path_missing_segment:{p}")
    return _eco_gate(
        GP08_ECO03_GATE_ID_V1,
        "synthesis_readiness_economics_admin_openapi_path_matrix",
        len(errors) == 0,
        {"errors": errors},
    )
