"""Phase 07 P07-25 — ``org_graph_retrieval`` tenant verification aggregate slice.

Normative: ``DOCS/cortex/retrieval/phase-07-verification-harness-spec.md`` (§Tenant);
**G-P07-TVER-01** golden slice law.

Bounded **integer-only** JSON suitable for certification excerpts (**FS-RTV-01**: no floats).
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
import zlib
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.retrieval.retrieval_addressing import retrieval_golden_vectors_v1_root
from vector.domains.cortex.retrieval.retrieval_index_materialization import get_published_index_epoch_v1
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry

ORG_GRAPH_RETRIEVAL_VERIFICATION_SLICE_SCHEMA_VERSION: Final[int] = 1

VECTOR_RETRIEVAL_TENANT_VERIFICATION_SLICE_ENV: Final[str] = (
    "VECTOR_RETRIEVAL_TENANT_VERIFICATION_SLICE"
)

RETRIEVAL_TENANT_VERIFICATION_SLICE_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/retrieval/tenant-verification-slice",
)

GP07_TVER01_GATE_ID_V1: Final[str] = "G-P07-TVER-01"

_WALK_INDEX_KINDS_V1: Final[frozenset[str]] = frozenset({"walk"})
_TCRE_INDEX_KINDS_V1: Final[frozenset[str]] = frozenset(
    {"materialization", "causal_chain", "causal_edge"}
)


def retrieval_tenant_verification_slice_enabled_v1() -> bool:
    return os.environ.get(VECTOR_RETRIEVAL_TENANT_VERIFICATION_SLICE_ENV, "").lower() in (
        "1",
        "true",
        "yes",
    )


def _golden_corpus_case_count_v1() -> int:
    root = retrieval_golden_vectors_v1_root()
    path = root / "corpus_manifest.json"
    if not path.is_file():
        return 0
    doc = json.loads(path.read_text(encoding="utf-8"))
    cases = doc.get("cases")
    return len(cases) if isinstance(cases, list) else 0


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
        return ["float_in_org_graph_retrieval_slice"]
    return []


def index_epoch_code_v1(index_epoch: str | None) -> int:
    """Stable integer pin for published ``index_epoch`` (0 when absent)."""
    if not index_epoch:
        return 0
    return int(zlib.crc32(index_epoch.encode("utf-8")) & 0xFFFFFFFF)


def validate_org_graph_retrieval_verification_slice_v1(doc: Mapping[str, Any]) -> list[str]:
    """Structural validation for **org_graph_retrieval** verification slice v1."""
    errors: list[str] = []
    errors.extend(list_fs_rtv01_slice_float_violations_v1(doc))
    required = (
        "index_epoch",
        "org_graph_retrieval_slice_schema_version",
        "retrieval_program_freeze_version",
        "tenant_id",
        "tcre_index_depth",
        "verification_run_id",
        "walk_index_depth",
    )
    for k in required:
        if k not in doc:
            errors.append(f"missing_key:{k}")
    if doc.get("org_graph_retrieval_slice_schema_version") != (
        ORG_GRAPH_RETRIEVAL_VERIFICATION_SLICE_SCHEMA_VERSION
    ):
        errors.append("schema_version_mismatch")
    if doc.get("retrieval_program_freeze_version") != PHASE07_PROGRAM_FREEZE_VERSION:
        errors.append("program_freeze_version_mismatch")
    for key in (
        "index_epoch",
        "org_graph_retrieval_slice_schema_version",
        "retrieval_program_freeze_version",
        "tcre_index_depth",
        "walk_index_depth",
    ):
        if key in doc and not isinstance(doc[key], int):
            errors.append(f"non_int:{key}")
    if "tenant_id" in doc and not isinstance(doc["tenant_id"], str):
        errors.append("tenant_id_not_str")
    vr = doc.get("verification_run_id")
    if vr is not None and not isinstance(vr, str):
        errors.append("verification_run_id_not_str_or_null")
    return errors


def compute_retrieval_verification_slice_hash_v1(slice_body: Mapping[str, Any]) -> str:
    """Deterministic sha256 over sorted compact JSON (**retrieval_slice_hash** law)."""
    payload = json.dumps(dict(slice_body), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _index_depth_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID,
    index_kinds: frozenset[str],
    published_epoch: str | None,
) -> int:
    if session is None:
        return 0
    stmt = (
        select(func.count())
        .select_from(CortexRetrievalIndexEntry)
        .where(
            CortexRetrievalIndexEntry.tenant_id == tenant_id,
            CortexRetrievalIndexEntry.index_kind.in_(sorted(index_kinds)),
        )
    )
    if published_epoch:
        stmt = stmt.where(CortexRetrievalIndexEntry.index_epoch == published_epoch)
    return int(session.scalar(stmt) or 0)


def build_org_graph_retrieval_verification_slice_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID | str,
    verification_run_id: str | None,
) -> dict[str, Any]:
    """Bounded ``org_graph_retrieval`` aggregate for tenant verification evidence (integers only)."""
    tid_uuid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    tid = str(tid_uuid)
    published = get_published_index_epoch_v1(session, tenant_id=tid_uuid) if session else None
    body: dict[str, Any] = {
        "index_epoch": index_epoch_code_v1(published),
        "org_graph_retrieval_slice_schema_version": (
            ORG_GRAPH_RETRIEVAL_VERIFICATION_SLICE_SCHEMA_VERSION
        ),
        "retrieval_program_freeze_version": int(PHASE07_PROGRAM_FREEZE_VERSION),
        "tenant_id": tid,
        "tcre_index_depth": _index_depth_v1(
            session,
            tenant_id=tid_uuid,
            index_kinds=_TCRE_INDEX_KINDS_V1,
            published_epoch=published,
        ),
        "verification_run_id": verification_run_id,
        "walk_index_depth": _index_depth_v1(
            session,
            tenant_id=tid_uuid,
            index_kinds=_WALK_INDEX_KINDS_V1,
            published_epoch=published,
        ),
    }
    return dict(sorted(body.items()))


def _tver_gate(errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_TVER01_GATE_ID_V1,
        "name": "gp07_tver01_org_graph_retrieval_slice_golden",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_tver01_org_graph_retrieval_slice_golden_static() -> dict[str, Any]:
    """**G-P07-TVER-01** — golden tenant ``org_graph_retrieval`` slice matches structural law."""
    errors: list[str] = []
    path = (
        retrieval_golden_vectors_v1_root()
        / "tenant_verification"
        / "org_graph_retrieval_slice_good_v1.json"
    )
    if not path.is_file():
        errors.append(f"missing_golden:{path}")
        return _tver_gate(errors)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            errors.append("golden_not_object")
            return _tver_gate(errors)
        errors.extend(validate_org_graph_retrieval_verification_slice_v1(doc))
        if doc.get("retrieval_program_freeze_version") != PHASE07_PROGRAM_FREEZE_VERSION:
            errors.append("golden_freeze_version_mismatch_normative")
        h1 = compute_retrieval_verification_slice_hash_v1(doc)
        h2 = compute_retrieval_verification_slice_hash_v1(doc)
        if h1 != h2:
            errors.append("slice_hash_non_deterministic")
        if _golden_corpus_case_count_v1() < 1:
            errors.append("golden_corpus_empty")
    except json.JSONDecodeError as exc:
        errors.append(f"json_invalid:{exc}")
    if errors:
        return _tver_gate(errors)
    built = build_org_graph_retrieval_verification_slice_v1(
        None,
        tenant_id=uuid.UUID(int=0),
        verification_run_id=None,
    )
    if built != doc:
        errors.append("golden_doc_mismatch_built_slice_for_zero_tenant")
    return _tver_gate(errors)


def verify_gp07_tver02_admin_openapi_path_matrix_static() -> dict[str, Any]:
    """Admin OpenAPI path tuple frozen for **GET …/tenant-verification-slice**."""
    errors: list[str] = []
    want = ("/admin/tenants/{tenant_id}/cortex/retrieval/tenant-verification-slice",)
    if RETRIEVAL_TENANT_VERIFICATION_SLICE_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    for p in RETRIEVAL_TENANT_VERIFICATION_SLICE_ADMIN_OPENAPI_PATHS_V1:
        if "cortex/retrieval/tenant-verification-slice" not in p:
            errors.append(f"path_missing_tenant_verification_segment:{p}")
    return {
        "id": "P07-25-tver-paths",
        "name": "retrieval_org_graph_retrieval_tenant_verification_slice_admin_openapi_path_matrix",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
