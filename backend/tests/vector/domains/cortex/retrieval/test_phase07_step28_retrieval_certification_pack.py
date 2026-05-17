"""P07-28 — **RETRIEVAL-CERT-PACK-1** + **G-P07-CLOSE-01** + admin path matrix."""

from __future__ import annotations

import base64
import uuid

from vector.domains.cortex.retrieval.retrieval_certification_pack import (
    PHASE07_RETRIEVAL_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
    RETRIEVAL_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1,
    RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    build_retrieval_certification_pack_snapshot_v1,
    build_retrieval_cert_pack_v1,
    compute_retrieval_vectors_bundle_hash_v1,
    default_retrieval_cert_pack_vector_files_v1,
    verify_gp07_close01_retrieval_cert_pack_closure_static,
    verify_gp07_rcpk01_retrieval_cert_pack_admin_openapi_path_matrix_static,
    verify_retrieval_cert_pack_v1,
)


def test_constants() -> None:
    assert PHASE07_RETRIEVAL_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION >= 1
    assert RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1 == "RETRIEVAL-CERT-PACK-1"
    assert RETRIEVAL_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1[0].endswith(
        "retrieval/certification-pack"
    )
    assert RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1 == (
        "manifest.json",
        "gate_results.json",
        "vectors/manifest.json",
        "legality_matrix.json",
        "policy_pack.sha256",
    )
    assert compute_retrieval_vectors_bundle_hash_v1().startswith("sha256:")


def test_all_step28_oracles_pass() -> None:
    rcpk = verify_gp07_rcpk01_retrieval_cert_pack_admin_openapi_path_matrix_static()
    assert rcpk["passed"] is True
    assert verify_gp07_close01_retrieval_cert_pack_closure_static()["passed"] is True


def test_build_retrieval_pack_roundtrip() -> None:
    gate_results = {
        "gates": [
            {
                "duration_ms": 0,
                "gate_id": "G-P07-ANTI-01",
                "status": "pass",
            }
        ],
        "manifest_digest": "",
        "stages_completed": ["A"],
    }
    pack = build_retrieval_cert_pack_v1(
        gate_results=gate_results,
        vector_files=default_retrieval_cert_pack_vector_files_v1(),
    )
    vr = verify_retrieval_cert_pack_v1(pack)
    assert vr.passed is True
    assert vr.errors == ()


def test_admin_contract_validates_snapshot() -> None:
    from vector.contracts.admin import AdminCortexRetrievalCertificationPackSnapshotResponse

    tid = uuid.uuid4()
    snap = build_retrieval_certification_pack_snapshot_v1(tenant_id=tid)
    AdminCortexRetrievalCertificationPackSnapshotResponse.model_validate(snap)


def test_operator_snapshot_happy_path() -> None:
    tid = uuid.uuid4()
    snap = build_retrieval_certification_pack_snapshot_v1(tenant_id=tid)
    assert snap["tenant_id"] == str(tid)
    assert snap["closure_passed"] is True
    assert snap["whole_file_sha256"] is not None
    assert snap["pack_gzip_base64"] is not None
    assert snap["pack_byte_length"] is not None
    raw = base64.b64decode(snap["pack_gzip_base64"])
    assert verify_retrieval_cert_pack_v1(raw).passed is True
