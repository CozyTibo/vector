"""Phase 08.5 Step 36 — constitutional freeze sign-off (**P085-FINAL-FREEZE**)."""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.operational_runtime.cesp_certification_pack import (
    P085_FINAL_FREEZE_BUNDLE_ID_V1,
    verify_gp085_close01_static,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_DOCTRINE_IMPLEMENTATION_STATUS_V1,
    PHASE085_STEP_PROGRAM_COUNT,
    build_phase085_normative_program_document_v1,
)

PHASE085_CONSTITUTIONAL_FREEZE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_DOCTRINE_FREEZE_STATUS_V1: Final[str] = "Frozen (implementation)"


def build_cesp_constitutional_freeze_banner_v1() -> dict[str, str]:
    return {
        "status": PHASE085_DOCTRINE_FREEZE_STATUS_V1,
        "bundle_id": P085_FINAL_FREEZE_BUNDLE_ID_V1,
        "headline": "Phase 08.5 CESP — implementation program frozen",
        "detail": (
            f"Steps 1–{PHASE085_STEP_PROGRAM_COUNT} runtime shipped; "
            "substrate operational maturation locked for Phase 09 handoff."
        ),
    }


def build_cesp_constitutional_freeze_signoff_snapshot_v1() -> dict[str, Any]:
    close = verify_gp085_close01_static()
    from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
        evaluate_phase09_readiness_v1,
    )

    from vector.infrastructure.db.session import session_scope

    with session_scope() as session:
        readiness = evaluate_phase09_readiness_v1(session)
    passed = bool(close.get("passed")) and bool(readiness.get("readiness_passed"))
    return {
        "constitutional_freeze_bundle": P085_FINAL_FREEZE_BUNDLE_ID_V1,
        "doctrine_freeze_status": PHASE085_DOCTRINE_FREEZE_STATUS_V1,
        "phase085_program_freeze_version": build_phase085_normative_program_document_v1().get(
            "phase085_program_freeze_version",
        ),
        "constitutional_freeze_passed": passed,
        "close_gate": close,
        "phase09_readiness": readiness,
        "freeze_banner": build_cesp_constitutional_freeze_banner_v1(),
    }


def build_cesp_constitutional_freeze_catalog_v1() -> dict[str, Any]:
    signoff = build_cesp_constitutional_freeze_signoff_snapshot_v1()
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_constitutional_freeze_runtime_schema_version": int(
            PHASE085_CONSTITUTIONAL_FREEZE_RUNTIME_SCHEMA_VERSION,
        ),
        "constitutional_freeze_bundle": P085_FINAL_FREEZE_BUNDLE_ID_V1,
        "doctrine_implementation_status": PHASE085_DOCTRINE_IMPLEMENTATION_STATUS_V1,
        "signoff_passed": bool(signoff.get("constitutional_freeze_passed")),
        "freeze_banner": build_cesp_constitutional_freeze_banner_v1(),
    }
