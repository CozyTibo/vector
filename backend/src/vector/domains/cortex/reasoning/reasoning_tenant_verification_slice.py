"""Phase 06 P06-34 — ``org_graph_reasoning`` tenant verification aggregate slice.

Normative: ``DOCS/cortex/reasoning/reasoning-verification-harness-spec.md`` (tenant slice +
readiness economics mirror **P05** Steps **23–25** intent);
``DOCS/cortex/reasoning/reasoning-admin-control-plane-spec.md`` (operator substrate).

Bounded **integer-only** JSON suitable for certification excerpts (**FS-RTV-01**: no floats).
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.normative import PHASE06_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.reasoning.reasoning_golden_thread_binding import (
    load_reasoning_corpus_manifest_v1,
    reasoning_golden_vectors_v1_root,
)

ORG_GRAPH_REASONING_VERIFICATION_SLICE_SCHEMA_VERSION: Final[int] = 1
VECTOR_REASONING_TENANT_VERIFICATION_SLICE_ENV: Final[str] = (
    "VECTOR_REASONING_TENANT_VERIFICATION_SLICE"
)

REASONING_TENANT_VERIFICATION_SLICE_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/reasoning/tenant-verification-slice",
)

_LAST_REASONING_GATE_BUNDLE_EMPTY_CANONICAL_SHA256: Final[str] = hashlib.sha256(
    json.dumps({}, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()


def reasoning_tenant_verification_slice_enabled_v1() -> bool:
    return os.environ.get(VECTOR_REASONING_TENANT_VERIFICATION_SLICE_ENV, "").lower() in (
        "1",
        "true",
        "yes",
    )


def _golden_corpus_case_count_v1() -> int:
    root = reasoning_golden_vectors_v1_root()
    manifest_path = root / "corpus_manifest.json"
    doc = load_reasoning_corpus_manifest_v1(manifest_path)
    cases = doc.get("cases")
    if not isinstance(cases, list):
        return 0
    return len(cases)


def _any_float(obj: Any) -> bool:
    if isinstance(obj, float):
        return True
    if isinstance(obj, dict):
        return any(_any_float(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_any_float(v) for v in obj)
    return False


def list_fs_rtv01_slice_float_violations_v1(slice_body: Mapping[str, Any]) -> list[str]:
    """**FS-RTV-01** — slice JSON must not carry floats (counts are integers only)."""
    if _any_float(slice_body):
        return ["float_in_org_graph_reasoning_slice"]
    return []


def validate_org_graph_reasoning_verification_slice_v1(doc: Mapping[str, Any]) -> list[str]:
    """Structural validation for **org_graph_reasoning** verification slice v1."""
    errors: list[str] = []
    errors.extend(list_fs_rtv01_slice_float_violations_v1(doc))
    required = (
        "golden_corpus_case_count",
        "last_reasoning_gate_bundle_sha256",
        "org_graph_reasoning_slice_schema_version",
        "phase06_program_freeze_version",
        "reasoning_gp06_gate_bundle_queue_depth_proxy",
        "tenant_id",
        "verification_run_id",
    )
    for k in required:
        if k not in doc:
            errors.append(f"missing_key:{k}")
    got_sv = doc.get("org_graph_reasoning_slice_schema_version")
    if got_sv != ORG_GRAPH_REASONING_VERIFICATION_SLICE_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if doc.get("phase06_program_freeze_version") != PHASE06_PROGRAM_FREEZE_VERSION:
        errors.append("program_freeze_version_mismatch")
    for key in (
        "golden_corpus_case_count",
        "reasoning_gp06_gate_bundle_queue_depth_proxy",
        "org_graph_reasoning_slice_schema_version",
        "phase06_program_freeze_version",
    ):
        if key in doc and not isinstance(doc[key], int):
            errors.append(f"non_int:{key}")
    if "tenant_id" in doc and not isinstance(doc["tenant_id"], str):
        errors.append("tenant_id_not_str")
    vr = doc.get("verification_run_id")
    if vr is not None and not isinstance(vr, str):
        errors.append("verification_run_id_not_str_or_null")
    return errors


def compute_reasoning_verification_slice_hash_v1(slice_body: Mapping[str, Any]) -> str:
    """Deterministic sha256 over sorted compact JSON."""
    payload = json.dumps(dict(slice_body), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _tcre_job_queue_depth_proxy_v1(session: Session | None, tenant_id: uuid.UUID) -> int:
    if session is None:
        return 0
    from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

    n = session.scalar(
        select(func.count())
        .select_from(CortexTcreReconstructionJob)
        .where(
            CortexTcreReconstructionJob.tenant_id == tenant_id,
            CortexTcreReconstructionJob.status.in_(("queued", "running")),
        )
    )
    return int(n or 0)


def _last_completed_job_aggregate_sha256_v1(session: Session | None, tenant_id: uuid.UUID) -> str:
    if session is None:
        return _LAST_REASONING_GATE_BUNDLE_EMPTY_CANONICAL_SHA256
    from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

    row = session.scalar(
        select(CortexTcreReconstructionJob)
        .where(
            CortexTcreReconstructionJob.tenant_id == tenant_id,
            CortexTcreReconstructionJob.status == "completed",
        )
        .order_by(CortexTcreReconstructionJob.completed_at.desc())
        .limit(1)
    )
    if row is None:
        return _LAST_REASONING_GATE_BUNDLE_EMPTY_CANONICAL_SHA256
    summary = row.summary_json or {}
    agg = summary.get("aggregate_digest")
    if isinstance(agg, str) and len(agg) == 64:
        return agg
    return _LAST_REASONING_GATE_BUNDLE_EMPTY_CANONICAL_SHA256


def build_org_graph_reasoning_verification_slice_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID | str,
    verification_run_id: str | None,
) -> dict[str, Any]:
    """Bounded ``org_graph_reasoning`` aggregate for tenant verification evidence (integers only)."""
    tid_uuid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    tid = str(tid_uuid)
    slice_sv = ORG_GRAPH_REASONING_VERIFICATION_SLICE_SCHEMA_VERSION
    body: dict[str, Any] = {
        "golden_corpus_case_count": int(_golden_corpus_case_count_v1()),
        "last_reasoning_gate_bundle_sha256": _last_completed_job_aggregate_sha256_v1(session, tid_uuid),
        "org_graph_reasoning_slice_schema_version": slice_sv,
        "phase06_program_freeze_version": int(PHASE06_PROGRAM_FREEZE_VERSION),
        "reasoning_gp06_gate_bundle_queue_depth_proxy": _tcre_job_queue_depth_proxy_v1(
            session,
            tid_uuid,
        ),
        "tenant_id": tid,
        "verification_run_id": verification_run_id,
    }
    return dict(sorted(body.items()))


def _rtvs_gate(errors: list[str]) -> dict[str, Any]:
    return {
        "id": "P06-34-rtvs-golden",
        "name": "reasoning_org_graph_reasoning_tenant_verification_slice_golden",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp06_rtvs01_org_graph_reasoning_slice_golden_static() -> dict[str, Any]:
    """Golden **org_graph_reasoning** slice matches structural law + program freeze version."""
    errors: list[str] = []
    path = (
        reasoning_golden_vectors_v1_root()
        / "tenant_verification"
        / "org_graph_reasoning_slice_good_v1.json"
    )
    if not path.is_file():
        errors.append(f"missing_golden:{path}")
        return _rtvs_gate(errors)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            errors.append("golden_not_object")
            return _rtvs_gate(errors)
        errors.extend(validate_org_graph_reasoning_verification_slice_v1(doc))
        if doc.get("phase06_program_freeze_version") != PHASE06_PROGRAM_FREEZE_VERSION:
            errors.append("golden_freeze_version_mismatch_normative")
        h1 = compute_reasoning_verification_slice_hash_v1(doc)
        h2 = compute_reasoning_verification_slice_hash_v1(doc)
        if h1 != h2:
            errors.append("slice_hash_non_deterministic")
    except json.JSONDecodeError as exc:
        errors.append(f"json_invalid:{exc}")
    if errors:
        return _rtvs_gate(errors)
    built = build_org_graph_reasoning_verification_slice_v1(
        None,
        tenant_id=uuid.UUID(int=0),
        verification_run_id=None,
    )
    if built != doc:
        errors.append("golden_doc_mismatch_built_slice_for_zero_tenant")
    return _rtvs_gate(errors)


def verify_gp06_rtvs02_admin_openapi_path_matrix_static() -> dict[str, Any]:
    """Admin OpenAPI path tuple frozen for **GET …/tenant-verification-slice**."""
    errors: list[str] = []
    want = ("/admin/tenants/{tenant_id}/cortex/reasoning/tenant-verification-slice",)
    if REASONING_TENANT_VERIFICATION_SLICE_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    for p in REASONING_TENANT_VERIFICATION_SLICE_ADMIN_OPENAPI_PATHS_V1:
        if "cortex/reasoning/tenant-verification-slice" not in p:
            errors.append(f"path_missing_tenant_verification_segment:{p}")
    return {
        "id": "P06-34-rtvs-paths",
        "name": "reasoning_org_graph_reasoning_tenant_verification_slice_admin_openapi_path_matrix",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
