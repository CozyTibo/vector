"""Phase 08.5 Step 01 — program freeze static gate (**G-P085-CESP-01**)."""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_FREEZE_BUNDLE_IDS,
    PHASE085_PROGRAM_FREEZE_VERSION,
    PHASE085_PROGRAM_ID_V1,
    PHASE085_STEP_PROGRAM_COUNT,
    build_phase085_normative_program_document_v1,
)

GP085_CESP01_GATE_ID_V1: Final[str] = "G-P085-CESP-01"


def verify_gp085_cesp01_program_freeze_static() -> dict[str, Any]:
    """**G-P085-CESP-01** — normative program freeze metadata matches P085-01 contract."""
    doc = build_phase085_normative_program_document_v1()
    failures: list[str] = []
    if doc.get("phase085_program_freeze_version") != PHASE085_PROGRAM_FREEZE_VERSION:
        failures.append("phase085_program_freeze_version_mismatch")
    if doc.get("program_id") != PHASE085_PROGRAM_ID_V1:
        failures.append("program_id_mismatch")
    if doc.get("step_program_count") != PHASE085_STEP_PROGRAM_COUNT:
        failures.append("step_program_count_mismatch")
    if doc.get("freeze_bundle_ids") != list(PHASE085_FREEZE_BUNDLE_IDS):
        failures.append("freeze_bundle_ids_mismatch")
    if doc.get("primary_gate_id") != GP085_CESP01_GATE_ID_V1:
        failures.append("primary_gate_id_mismatch")
    if not doc.get("executive_brief_fixture_digest_sha256"):
        failures.append("executive_brief_digest_missing")
    passed = not failures
    return {
        "id": GP085_CESP01_GATE_ID_V1,
        "passed": passed,
        "gate_id": GP085_CESP01_GATE_ID_V1,
        "failure_codes": failures,
        "phase085_program_freeze_version": int(PHASE085_PROGRAM_FREEZE_VERSION),
        "step_program_count": int(PHASE085_STEP_PROGRAM_COUNT),
    }
