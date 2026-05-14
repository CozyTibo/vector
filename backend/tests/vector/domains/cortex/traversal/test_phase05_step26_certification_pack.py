"""P05-26 — **OCTS-CERT-PACK-1** + **G-P05-CLOSE-01**."""

from __future__ import annotations

from vector.domains.cortex.traversal.certification_pack import (
    build_oct_cert_pack_v1,
    default_oct_cert_pack_vector_files_v1,
    verify_gp05_close01_oct_cert_pack_static,
    verify_oct_cert_pack_v1,
)
from vector.domains.cortex.traversal.verification_gates_catalog import run_octs_wired_verification_stages_v1


def test_verify_oct_cert_pack_round_trip() -> None:
    gate_results = {
        "gates": [
            {"duration_ms": 0, "gate_id": "G-P05-LEGAL-01", "status": "pass"},
        ],
        "manifest_digest": "",
        "stages_completed": ["A", "B", "C", "D", "E", "Z"],
    }
    pack = build_oct_cert_pack_v1(
        gate_results=gate_results,
        vector_files=default_oct_cert_pack_vector_files_v1(),
    )
    vr = verify_oct_cert_pack_v1(pack)
    assert vr.passed is True, vr.errors


def test_tamper_one_byte_fails_verify() -> None:
    gate_results = {
        "gates": [{"duration_ms": 0, "gate_id": "G-P05-LEGAL-01", "status": "pass"}],
        "manifest_digest": "",
        "stages_completed": ["A", "B", "C", "D", "E", "Z"],
    }
    pack = bytearray(
        build_oct_cert_pack_v1(
            gate_results=gate_results,
            vector_files=default_oct_cert_pack_vector_files_v1(),
        )
    )
    idx = max(1, len(pack) // 2)
    pack[idx] ^= 0xFF
    vr = verify_oct_cert_pack_v1(bytes(pack))
    assert vr.passed is False
    assert any("gunzip" in e or "payload" in e for e in vr.errors)


def test_gp05_close01_static_passes() -> None:
    out = verify_gp05_close01_oct_cert_pack_static()
    assert out["id"] == "G-P05-CLOSE-01"
    assert out["passed"] is True, out


def test_stage_z_runs_close_after_tver() -> None:
    out = run_octs_wired_verification_stages_v1(("Z",))
    assert out["passed"] is True, out
    order = [x["gate_id"] for x in out["results"]]
    assert order.index("G-P05-TVER-01") < order.index("G-P05-CLOSE-01")
