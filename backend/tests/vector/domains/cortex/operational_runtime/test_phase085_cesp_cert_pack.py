"""P085-36 — **CESP-CERT-PACK-1** + **G-P085-CLOSE-01**."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_certification_pack import (
    CESP_CERT_PACK_FORMAT_LITERAL_V1,
    CESP_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    build_cesp_cert_pack_v1,
    build_policy_thresholds_payload_v1,
    run_all_cesp_gp085_static_gates_v1,
    run_cesp_ci_cert_pack_artifact_v1,
    verify_cesp_cert_pack_v1,
    verify_gp085_close01_cesp_cert_pack_shape_reference_static,
    verify_gp085_close01_static,
)
from vector.domains.cortex.operational_runtime.cesp_closure_gates import (
    verify_gp085_close01_static as verify_close_from_closure_module,
)
from vector.domains.cortex.operational_runtime.cesp_constitutional_freeze import (
    build_cesp_constitutional_freeze_signoff_snapshot_v1,
)


def test_constants() -> None:
    assert CESP_CERT_PACK_FORMAT_LITERAL_V1 == "CESP-CERT-PACK-1"
    assert CESP_CERT_PACK_REQUIRED_ROOT_FILES_V1 == (
        "manifest.json",
        "gate_results.json",
        "golden_tenant_slice.json",
        "soak_summary.json",
        "readiness_checklist.json",
        "policy_thresholds.json",
    )
    policy = build_policy_thresholds_payload_v1()
    assert "theta_tcre_saturation" in policy
    assert "caps" in policy


def test_all_wired_gates_pass_except_close() -> None:
    rows = run_all_cesp_gp085_static_gates_v1(skip_gate_ids=frozenset({"G-P085-CLOSE-01"}))
    assert rows
    assert all(r["status"] == "pass" for r in rows)


def test_shape_reference_static() -> None:
    assert verify_gp085_close01_cesp_cert_pack_shape_reference_static()["passed"] is True


def test_build_pack_roundtrip() -> None:
    gate_results = {
        "gates": [
            {"duration_ms": 0, "gate_id": "G-P085-CESP-01", "status": "pass"},
        ],
        "manifest_digest": "",
        "program_step": 36,
    }
    pack = build_cesp_cert_pack_v1(
        gate_results=gate_results,
        golden_tenant_slice={"profile_spec": {}},
        soak_summary={"soak_window_days": 7},
        readiness_checklist={"checklist": [], "readiness_passed": True},
        policy_thresholds=build_policy_thresholds_payload_v1(),
    )
    vr = verify_cesp_cert_pack_v1(pack)
    assert vr.passed is True
    assert vr.errors == ()


@pytest.mark.integration
def test_close01_closure_static(db_session: Session) -> None:
    from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
        record_phase09_soak_signoff_v1,
    )

    record_phase09_soak_signoff_v1(db_session, note="pytest close01")
    db_session.commit()
    assert verify_gp085_close01_static()["passed"] is True
    assert verify_close_from_closure_module()["passed"] is True


@pytest.mark.integration
def test_ci_cert_pack_artifact(db_session: Session) -> None:
    from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
        record_phase09_soak_signoff_v1,
    )

    record_phase09_soak_signoff_v1(db_session, note="pytest ci cert")
    db_session.commit()
    out = run_cesp_ci_cert_pack_artifact_v1()
    assert out["passed"] is True
    assert out["verify_passed"] is True


@pytest.mark.integration
def test_constitutional_freeze_signoff(db_session: Session) -> None:
    from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
        record_phase09_soak_signoff_v1,
    )

    record_phase09_soak_signoff_v1(db_session, note="pytest freeze")
    db_session.commit()
    snap = build_cesp_constitutional_freeze_signoff_snapshot_v1()
    assert snap["constitutional_freeze_passed"] is True
