"""Phase 08 P08-24 — ``org_graph_synthesis`` tenant verification slice (**G-P08-TVER-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-evaluation-quality-governance.md`` §Tenant.
Bounded **integer-only** JSON suitable for certification excerpts (**FS-STV-01**: no floats).
"""

from __future__ import annotations

import json
import os
import uuid
import zlib
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.normative import PHASE08_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.synthesis.synthesis_bounded_caps import SD_LLM_SCHEMA_V1
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_synthesized_scopes_v1,
    pipeline_default_workloads_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    SYNTHESIS_WORKLOAD_CLASS_METADATA_V1,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    verify_gp08_replay01_double_run_match_static,
)
from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
    synthesis_golden_corpus_case_count_v1,
    synthesis_golden_vectors_v1_root,
)
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

ORG_GRAPH_SYNTHESIS_VERIFICATION_SLICE_SCHEMA_VERSION: Final[int] = 1

VECTOR_SYNTHESIS_TENANT_VERIFICATION_SLICE_ENV: Final[str] = (
    "VECTOR_SYNTHESIS_TENANT_VERIFICATION_SLICE"
)

GP08_TVER01_GATE_ID_V1: Final[str] = "G-P08-TVER-01"

SYNTHESIS_TENANT_VERIFICATION_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-evaluation-quality-governance.md"
)

SYNTHESIS_SUBSTRATE_VERIFICATION_CONTRACT_V1: Final[str] = "synthesis_substrate_verification_v1"

SYNTHESIS_TENANT_VERIFICATION_SLICE_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/synthesis/tenant-verification-slice",
)

_STALE_JOB_HOURS_V1: Final[int] = 24
_LLM_SCHEMA_LOOKBACK_DAYS_V1: Final[int] = 7


def synthesis_tenant_verification_slice_enabled_v1() -> bool:
    return os.environ.get(VECTOR_SYNTHESIS_TENANT_VERIFICATION_SLICE_ENV, "").lower() in (
        "1",
        "true",
        "yes",
    )


def _golden_corpus_case_count_v1() -> int:
    return synthesis_golden_corpus_case_count_v1()


def _any_float(obj: Any) -> bool:
    if isinstance(obj, float):
        return True
    if isinstance(obj, dict):
        return any(_any_float(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_any_float(v) for v in obj)
    return False


def list_fs_stv01_slice_float_violations_v1(slice_body: Mapping[str, Any]) -> list[str]:
    """**FS-STV-01** — slice JSON must not carry floats."""
    if _any_float(slice_body):
        return ["float_in_org_graph_synthesis_slice"]
    return []


def publication_epoch_code_v1(publication_epoch: str | None) -> int:
    if not publication_epoch:
        return 0
    return int(zlib.crc32(publication_epoch.encode("utf-8")) & 0xFFFFFFFF)


def validate_org_graph_synthesis_verification_slice_v1(doc: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    errors.extend(list_fs_stv01_slice_float_violations_v1(doc))
    required = (
        "completed_jobs_count",
        "eligible_scopes",
        "golden_corpus_case_count",
        "org_graph_synthesis_slice_schema_version",
        "phase08_program_freeze_version",
        "publication_epoch_code",
        "synthesis_job_queue_depth_proxy",
        "synthesized_scopes",
        "tenant_id",
        "verification_run_id",
    )
    for k in required:
        if k not in doc:
            errors.append(f"missing_key:{k}")
    if doc.get("org_graph_synthesis_slice_schema_version") != (
        ORG_GRAPH_SYNTHESIS_VERIFICATION_SLICE_SCHEMA_VERSION
    ):
        errors.append("schema_version_mismatch")
    if doc.get("phase08_program_freeze_version") != PHASE08_PROGRAM_FREEZE_VERSION:
        errors.append("program_freeze_version_mismatch")
    for key in (
        "completed_jobs_count",
        "eligible_scopes",
        "golden_corpus_case_count",
        "org_graph_synthesis_slice_schema_version",
        "phase08_program_freeze_version",
        "publication_epoch_code",
        "synthesis_job_queue_depth_proxy",
        "synthesized_scopes",
    ):
        if key in doc and not isinstance(doc[key], int):
            errors.append(f"non_int:{key}")
    if "tenant_id" in doc and not isinstance(doc["tenant_id"], str):
        errors.append("tenant_id_not_str")
    vr = doc.get("verification_run_id")
    if vr is not None and not isinstance(vr, str):
        errors.append("verification_run_id_not_str_or_null")
    return errors


def compute_synthesis_verification_slice_hash_v1(slice_body: Mapping[str, Any]) -> str:
    import hashlib

    payload = json.dumps(dict(slice_body), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _synthesis_job_queue_depth_proxy_v1(session: Session | None, tenant_id: uuid.UUID) -> int:
    if session is None:
        return 0
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status.in_(("queued", "running")),
            )
        )
        or 0
    )


def _completed_jobs_count_v1(session: Session | None, tenant_id: uuid.UUID) -> int:
    if session is None:
        return 0
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "completed",
            )
        )
        or 0
    )


def _last_completed_job_at_v1(session: Session, tenant_id: uuid.UUID) -> datetime | None:
    row = session.scalar(
        select(CortexSynthesisJob.completed_at)
        .where(
            CortexSynthesisJob.tenant_id == tenant_id,
            CortexSynthesisJob.status == "completed",
            CortexSynthesisJob.completed_at.isnot(None),
        )
        .order_by(CortexSynthesisJob.completed_at.desc())
        .limit(1)
    )
    return row if isinstance(row, datetime) else None


def _llm_schema_failure_count_7d_v1(session: Session, tenant_id: uuid.UUID) -> int:
    cutoff = datetime.now(tz=UTC) - timedelta(days=_LLM_SCHEMA_LOOKBACK_DAYS_V1)
    rows = session.scalars(
        select(CortexSynthesisJob).where(
            CortexSynthesisJob.tenant_id == tenant_id,
            CortexSynthesisJob.completed_at.isnot(None),
            CortexSynthesisJob.completed_at >= cutoff,
        )
    ).all()
    count = 0
    for job in rows:
        receipt = dict(job.receipt_json or {})
        for row in list(receipt.get("synthesis_omission_rows") or []):
            if not isinstance(row, dict):
                continue
            sd = str(row.get("sd_code") or row.get("synthesis_omission_class") or "")
            if sd == SD_LLM_SCHEMA_V1:
                count += 1
    return count


def _has_default_workload_artifact_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    workloads: list[str],
) -> bool:
    kinds = {
        str((SYNTHESIS_WORKLOAD_CLASS_METADATA_V1.get(w) or {}).get("primary_artifact_kind") or w)
        for w in workloads
    }
    kinds.discard("internal cert only")
    kinds.discard("per tenant default")
    if not kinds:
        return False
    n = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisArtifact)
            .where(
                CortexSynthesisArtifact.tenant_id == tenant_id,
                CortexSynthesisArtifact.artifact_kind.in_(sorted(kinds)),
            )
        )
        or 0
    )
    return n > 0


def build_org_graph_synthesis_verification_slice_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID | str,
    verification_run_id: str | None,
) -> dict[str, Any]:
    """Bounded ``org_graph_synthesis`` aggregate for tenant verification evidence."""
    tid_uuid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    tid = str(tid_uuid)
    eligible = 0
    synthesized = 0
    pub_epoch: str | None = None
    if session is not None:
        scope = count_synthesis_synthesized_scopes_v1(session, tenant_id=tid_uuid)
        eligible = int(scope.get("eligible_scopes", 0))
        synthesized = int(scope.get("synthesized_scopes", 0))
        pub_epoch = scope.get("synthesis_publication_epoch")
    body: dict[str, Any] = {
        "completed_jobs_count": _completed_jobs_count_v1(session, tid_uuid),
        "eligible_scopes": eligible,
        "golden_corpus_case_count": int(_golden_corpus_case_count_v1()),
        "org_graph_synthesis_slice_schema_version": (
            ORG_GRAPH_SYNTHESIS_VERIFICATION_SLICE_SCHEMA_VERSION
        ),
        "phase08_program_freeze_version": int(PHASE08_PROGRAM_FREEZE_VERSION),
        "publication_epoch_code": publication_epoch_code_v1(
            str(pub_epoch) if pub_epoch else None
        ),
        "synthesis_job_queue_depth_proxy": _synthesis_job_queue_depth_proxy_v1(session, tid_uuid),
        "synthesized_scopes": synthesized,
        "tenant_id": tid,
        "verification_run_id": verification_run_id,
    }
    return dict(sorted(body.items()))


def verify_tenant_synthesis_slice_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant synthesis substrate checks for operator verification extension."""
    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    scope = count_synthesis_synthesized_scopes_v1(session, tenant_id=tenant_id)
    eligible = int(scope.get("eligible_scopes", 0))
    idle = eligible == 0
    pub_epoch = scope.get("synthesis_publication_epoch")

    pub_ok = bool(pub_epoch) or idle
    if not pub_ok:
        failures.append("no_synthesis_publication_epoch")
    checks.append(
        {
            "check_id": "publication_epoch_exists",
            "passed": pub_ok,
            "failure_code": None if pub_ok else "no_synthesis_publication_epoch",
        }
    )

    workloads = pipeline_default_workloads_v1()
    has_default = _has_default_workload_artifact_v1(session, tenant_id=tenant_id, workloads=workloads)
    default_ok = has_default or idle or int(scope.get("artifact_total", 0)) == 0
    if not default_ok:
        failures.append("no_default_artifact")
    checks.append(
        {
            "check_id": "default_workload_artifact_exists",
            "passed": default_ok,
            "failure_code": None if default_ok else "no_default_artifact",
        }
    )

    last_at = _last_completed_job_at_v1(session, tenant_id)
    now = datetime.now(tz=UTC)
    stale = False
    if not idle and last_at is None:
        stale = True
    elif not idle and last_at is not None:
        stale = last_at < now - timedelta(hours=_STALE_JOB_HOURS_V1)
    stale_ok = not stale
    if stale:
        failures.append("synthesis_stale")
    checks.append(
        {
            "check_id": "last_job_fresh_or_idle",
            "passed": stale_ok,
            "failure_code": None if stale_ok else "synthesis_stale",
        }
    )

    schema_count = _llm_schema_failure_count_7d_v1(session, tenant_id)
    schema_ok = schema_count == 0
    if not schema_ok:
        failures.append("llm_schema_failures")
    checks.append(
        {
            "check_id": "sd_llm_schema_zero_7d",
            "passed": schema_ok,
            "failure_code": None if schema_ok else "llm_schema_failures",
            "sd_llm_schema_count_7d": schema_count,
        }
    )

    replay_gate = verify_gp08_replay01_double_run_match_static()
    replay_ok = bool(replay_gate.get("passed"))
    if not replay_ok:
        failures.append("replay_twin_failed")
    checks.append(
        {
            "check_id": "gp08_replay01_sample",
            "passed": replay_ok,
            "failure_code": None if replay_ok else "replay_twin_failed",
            "gate_id": "G-P08-REPLAY-01",
        }
    )

    slice_body = build_org_graph_synthesis_verification_slice_v1(
        session,
        tenant_id=tenant_id,
        verification_run_id=None,
    )
    return {
        "surface_kind": "verification_probe",
        "synthesis_substrate_contract": SYNTHESIS_SUBSTRATE_VERIFICATION_CONTRACT_V1,
        "gate_id": GP08_TVER01_GATE_ID_V1,
        "spec_ref": SYNTHESIS_TENANT_VERIFICATION_SPEC_REF_V1,
        "tenant_id": str(tenant_id),
        "passed": len(failures) == 0,
        "failure_codes": failures,
        "checks": checks,
        "idle_tenant": idle,
        "synthesis_substrate": {
            "passed": len(failures) == 0,
            "failure_codes": failures,
            "checks": checks,
        },
        "slice": slice_body,
        "synthesis_slice_hash": compute_synthesis_verification_slice_hash_v1(slice_body),
    }


def _tver_gate(errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_TVER01_GATE_ID_V1,
        "name": "gp08_tver01_org_graph_synthesis_slice_golden",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_tver01_org_graph_synthesis_slice_golden_static() -> dict[str, Any]:
    """**G-P08-TVER-01** — golden tenant ``org_graph_synthesis`` slice matches structural law."""
    errors: list[str] = []
    path = (
        synthesis_golden_vectors_v1_root()
        / "tenant_verification"
        / "org_graph_synthesis_slice_good_v1.json"
    )
    if not path.is_file():
        errors.append(f"missing_golden:{path}")
        return _tver_gate(errors)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            errors.append("golden_not_object")
            return _tver_gate(errors)
        errors.extend(validate_org_graph_synthesis_verification_slice_v1(doc))
        if doc.get("phase08_program_freeze_version") != PHASE08_PROGRAM_FREEZE_VERSION:
            errors.append("golden_freeze_version_mismatch_normative")
        h1 = compute_synthesis_verification_slice_hash_v1(doc)
        h2 = compute_synthesis_verification_slice_hash_v1(doc)
        if h1 != h2:
            errors.append("slice_hash_non_deterministic")
        if _golden_corpus_case_count_v1() < 1:
            errors.append("golden_corpus_empty")
    except json.JSONDecodeError as exc:
        errors.append(f"json_invalid:{exc}")
    if errors:
        return _tver_gate(errors)
    built = build_org_graph_synthesis_verification_slice_v1(
        None,
        tenant_id=uuid.UUID(int=0),
        verification_run_id=None,
    )
    if built != doc:
        errors.append("golden_doc_mismatch_built_slice_for_zero_tenant")
    return _tver_gate(errors)


def verify_gp08_tver02_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = ("/admin/tenants/{tenant_id}/cortex/synthesis/tenant-verification-slice",)
    if SYNTHESIS_TENANT_VERIFICATION_SLICE_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    return {
        "id": "P08-24-tver-paths",
        "name": "synthesis_org_graph_synthesis_tenant_verification_slice_admin_openapi_path_matrix",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
