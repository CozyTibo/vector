"""P06-35 — **TCRE-CERT-PACK-1** + **G-P06-CLOSE-01** + admin path matrix."""

from __future__ import annotations

import base64
import uuid

from vector.domains.cortex.reasoning.reasoning_certification_pack import (
    PHASE06_REASONING_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION,
    REASONING_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1,
    TCRE_CERT_PACK_FORMAT_LITERAL_V1,
    TCRE_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    build_reasoning_certification_pack_snapshot_v1,
    build_tcre_cert_pack_v1,
    default_tcre_cert_pack_vector_files_v1,
    verify_gp06_close01_tcre_cert_pack_closure_static,
    verify_gp06_rcpk01_reasoning_cert_pack_admin_openapi_path_matrix_static,
    verify_tcre_cert_pack_v1,
)


def test_constants() -> None:
    assert PHASE06_REASONING_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION >= 1
    assert TCRE_CERT_PACK_FORMAT_LITERAL_V1 == "TCRE-CERT-PACK-1"
    assert REASONING_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1[0].endswith(
        "reasoning/certification-pack"
    )
    assert TCRE_CERT_PACK_REQUIRED_ROOT_FILES_V1 == (
        "manifest.json",
        "gate_results.json",
        "vectors/manifest.json",
    )


def test_all_step35_oracles_pass() -> None:
    rcpk = verify_gp06_rcpk01_reasoning_cert_pack_admin_openapi_path_matrix_static()
    assert rcpk["passed"] is True
    assert verify_gp06_close01_tcre_cert_pack_closure_static()["passed"] is True


def test_build_tcre_pack_roundtrip() -> None:
    gate_results = {
        "gates": [
            {
                "duration_ms": 0,
                "gate_id": "G-P06-ANTI-01",
                "status": "pass",
            }
        ],
        "manifest_digest": "",
        "stages_completed": ["A"],
    }
    pack = build_tcre_cert_pack_v1(
        gate_results=gate_results,
        vector_files=default_tcre_cert_pack_vector_files_v1(),
    )
    vr = verify_tcre_cert_pack_v1(pack)
    assert vr.passed is True
    assert vr.errors == ()


def test_admin_contract_validates_snapshot() -> None:
    from vector.contracts.admin import AdminCortexReasoningCertificationPackSnapshotResponse

    tid = uuid.uuid4()
    snap = build_reasoning_certification_pack_snapshot_v1(tenant_id=tid)
    AdminCortexReasoningCertificationPackSnapshotResponse.model_validate(snap)


def test_operator_snapshot_happy_path() -> None:
    tid = uuid.uuid4()
    snap = build_reasoning_certification_pack_snapshot_v1(tenant_id=tid)
    assert snap["tenant_id"] == str(tid)
    assert snap["closure_passed"] is True
    assert snap["whole_file_sha256"] is not None
    assert snap["pack_gzip_base64"] is not None
    assert snap["pack_byte_length"] is not None
    raw = base64.b64decode(snap["pack_gzip_base64"])
    assert verify_tcre_cert_pack_v1(raw).passed is True
