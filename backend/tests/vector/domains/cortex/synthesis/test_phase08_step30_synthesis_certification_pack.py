"""P08-30 — **SYNTHESIS-CERT-PACK-1** + **G-P08-CLOSE-01** + admin path matrix."""

from __future__ import annotations

import uuid

from vector.domains.cortex.synthesis.synthesis_certification_pack import (
    PHASE08_SYNTHESIS_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
    SYNTHESIS_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1,
    SYNTHESIS_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    build_synthesis_certification_pack_snapshot_v1,
    build_synthesis_cert_pack_v1,
    compute_synthesis_vectors_bundle_hash_v1,
    default_synthesis_cert_pack_vector_files_v1,
    run_synthesis_gp08_ci_cert_pack_artifact_v1,
    verify_gp08_close01_synthesis_cert_pack_closure_static,
    verify_gp08_scpk01_synthesis_cert_pack_admin_openapi_path_matrix_static,
    verify_synthesis_cert_pack_v1,
)


def test_constants() -> None:
    assert PHASE08_SYNTHESIS_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION >= 1
    assert SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1 == "SYNTHESIS-CERT-PACK-1"
    assert SYNTHESIS_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1[0].endswith(
        "synthesis/certification-pack",
    )
    assert SYNTHESIS_CERT_PACK_REQUIRED_ROOT_FILES_V1 == (
        "manifest.json",
        "gate_results.json",
        "vectors/manifest.json",
        "legality_matrix.json",
        "policy_pack.sha256",
    )
    assert len(compute_synthesis_vectors_bundle_hash_v1()) == 64


def test_all_step30_cert_oracles_pass() -> None:
    assert verify_gp08_scpk01_synthesis_cert_pack_admin_openapi_path_matrix_static()["passed"] is True
    assert verify_gp08_close01_synthesis_cert_pack_closure_static()["passed"] is True


def test_build_synthesis_pack_roundtrip() -> None:
    gate_results = {
        "gates": [
            {
                "duration_ms": 0,
                "gate_id": "G-P08-ANTI-01",
                "status": "pass",
            },
        ],
        "manifest_digest": "",
        "stages_completed": ["A"],
    }
    pack = build_synthesis_cert_pack_v1(
        gate_results=gate_results,
        vector_files=default_synthesis_cert_pack_vector_files_v1(),
    )
    vr = verify_synthesis_cert_pack_v1(pack)
    assert vr.passed is True
    assert vr.errors == ()


def test_ci_cert_pack_artifact() -> None:
    out = run_synthesis_gp08_ci_cert_pack_artifact_v1()
    assert out["passed"] is True
    assert out["verify_passed"] is True


def test_operator_snapshot_happy_path() -> None:
    tid = uuid.uuid4()
    snap = build_synthesis_certification_pack_snapshot_v1(tenant_id=tid)
    assert snap["tenant_id"] == str(tid)
    assert snap["closure_passed"] is True
    assert snap["whole_file_sha256"] is not None
    assert snap["pack_gzip_base64"] is not None
