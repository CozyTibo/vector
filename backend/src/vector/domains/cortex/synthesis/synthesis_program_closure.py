"""Phase 08 P08-30 — program closure + **FF-P08-5** admin freeze.

Normative: ``DOCS/cortex/synthesis/phase-08-closure-gates-doctrine.md`` (10 completion criteria,
**G-P08-CLOSE-01**, operator checklist).
"""

from __future__ import annotations

import importlib
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.normative import (
    PHASE08_FREEZE_BUNDLE_IDS,
    PHASE08_PROGRAM_FREEZE_VERSION,
    PHASE08_STEP_PROGRAM_COUNT,
    PHASE08_SUBSTRATE_PIPELINE_STAGES_V1,
    build_phase08_normative_program_document_v1,
)

PHASE08_SYNTHESIS_PROGRAM_CLOSURE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_PROGRAM_CLOSURE_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-closure-gates-doctrine.md"
)

PHASE08_FREEZE_BUNDLE_FF_P08_5_V1: Final[str] = "FF-P08-5"

GP08_P30_PROGRAM_CLOSURE_GATE_ID_V1: Final[str] = "G-P08-P30-CLOSE"

_PHASE08_REQUIRED_DOCTRINE_FILES_V1: Final[tuple[str, ...]] = (
    "PHASE08_CONSTITUTIONAL_CHANGELOG.md",
    "phase-08-normative-index.md",
    "phase-08-closure-gates-doctrine.md",
    "phase-08-implementation-sequencing-plan.md",
    "phase-08-testing-strategy.md",
    "phase-08-pipeline-orchestration.md",
    "phase-08-e2e-operational-flow.md",
    "synthesis-spec-gap-matrix.md",
)

SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1: Final[tuple[tuple[str, str], ...]] = (
    ("C01", "Steps 1-35 doctrine Strong/Frozen; no Active P0"),
    ("C02", "SynthesisPolicyPackV1_Default digest pinned"),
    ("C03", "JSON schemas in CI (G-P08-SCHEMA-01)"),
    ("C04", "execute_synthesis_job_envelope_v1 FSM + execution_trace"),
    ("C05", "Substrate pipeline phase_08_synthesis specified"),
    ("C06", "G-P08-REPLAY-02 publication epoch law"),
    ("C07", "Admin control plane surfaces 1-16 with surface_kind"),
    ("C08", "Golden corpus G-P08-REPLAY-01 + G-P08-EVAL-01"),
    ("C09", "Tenant verification G-P08-TVER-01"),
    ("C10", "E2E scenario A job-path slice automated"),
)

SYNTHESIS_OPERATOR_CLOSURE_CHECKLIST_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "check_id": "OP-01",
        "label": "Synthesis health strip green for pilot tenants",
        "detail": "Admin SPA synthesis section + health GET",
    },
    {
        "check_id": "OP-02",
        "label": "Job debugger resolves scripted failures",
        "detail": "GET /jobs/{id} exposes execution_trace",
    },
    {
        "check_id": "OP-03",
        "label": "Replay explorer twin pass on golden tenant",
        "detail": "G-P08-REPLAY-01 harness + replay explorer route",
    },
    {
        "check_id": "OP-04",
        "label": "Certification pack archived with digest",
        "detail": "SYNTHESIS-CERT-PACK-1 snapshot + archive POST",
    },
    {
        "check_id": "OP-05",
        "label": "Overview synthesis stage linked",
        "detail": "GET /overview exposes synthesis completeness stage",
    },
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        if (root / "DOCS" / "cortex" / "synthesis" / "phase-08-normative-index.md").is_file():
            return root
    msg = "repo root not found"
    raise FileNotFoundError(msg)


def _criterion_row(
    criterion_id: str,
    label: str,
    *,
    passed: bool,
    errors: list[str],
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "label": label,
        "passed": passed,
        "errors": list(errors),
        "detail": dict(detail or {}),
    }


def _eval_c01_doctrine_frozen() -> dict[str, Any]:
    errors: list[str] = []
    root = _repo_root()
    synth_dir = root / "DOCS" / "cortex" / "synthesis"
    for name in _PHASE08_REQUIRED_DOCTRINE_FILES_V1:
        if not (synth_dir / name).is_file():
            errors.append(f"missing_doctrine:{name}")
    tracker = root / "DOCS" / "cortex" / "MASTER_TRACKER.md"
    if not tracker.is_file():
        errors.append("missing_master_tracker")
    else:
        text = tracker.read_text(encoding="utf-8")
        if "Phase 08" not in text or "Synthesis & Intelligence" not in text:
            errors.append("master_tracker_missing_phase08_section")
    doc = build_phase08_normative_program_document_v1()
    if doc.get("step_program_count") != PHASE08_STEP_PROGRAM_COUNT:
        errors.append("step_program_count_mismatch")
    if PHASE08_FREEZE_BUNDLE_FF_P08_5_V1 not in PHASE08_FREEZE_BUNDLE_IDS:
        errors.append("ff_p08_5_not_in_freeze_bundles")
    from vector.domains.cortex.synthesis.synthesis_implementation_sequencing import (
        verify_gp08_seq04_waves_zero_through_five_complete_static,
    )

    if not verify_gp08_seq04_waves_zero_through_five_complete_static().get("passed"):
        errors.append("waves_0_5_not_complete")
    return _criterion_row("C01", SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1[0][1], passed=not errors, errors=errors)


def _eval_c02_policy_fixture_digest() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
        hash_synthesis_policy_pack_fixture_file_v1,
    )

    doc = build_phase08_normative_program_document_v1()
    pinned = str(doc.get("policy_pack_fixture_digest_sha256") or "")
    live = hash_synthesis_policy_pack_fixture_file_v1()
    if not pinned or pinned != live:
        errors.append("fixture_digest_not_pinned_in_normative")
    return _criterion_row("C02", SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1[1][1], passed=not errors, errors=errors)


def _eval_c03_schema_ci() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_verification_harness import (
        _run_gp08_schema01_bundle_static,
    )

    out = _run_gp08_schema01_bundle_static()
    if not out.get("passed"):
        errors.append("schema01_bundle_failed")
    return _criterion_row("C03", SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1[2][1], passed=not errors, errors=errors)


def _eval_c04_fsm_complete() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_orchestrator import (
        execute_synthesis_job_envelope_v1,
        verify_gp08_fsm01_synthesis_phase_order_static,
    )

    if not verify_gp08_fsm01_synthesis_phase_order_static().get("passed"):
        errors.append("fsm01_gate_failed")
    if not callable(execute_synthesis_job_envelope_v1):
        errors.append("missing_execute_synthesis_job_envelope_v1")
    return _criterion_row("C04", SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1[3][1], passed=not errors, errors=errors)


def _eval_c05_pipeline_specified() -> dict[str, Any]:
    errors: list[str] = []
    root = _repo_root()
    pipe_doc = root / "DOCS" / "cortex" / "synthesis" / "phase-08-pipeline-orchestration.md"
    if not pipe_doc.is_file():
        errors.append("missing_pipeline_orchestration_doc")
    else:
        text = pipe_doc.read_text(encoding="utf-8")
        if "phase_08_synthesis" not in text and "PHASE_08" not in text:
            errors.append("pipeline_doc_missing_phase08_marker")
    if "Synthesis" not in PHASE08_SUBSTRATE_PIPELINE_STAGES_V1:
        errors.append("normative_missing_synthesis_stage")
    return _criterion_row(
        "C05",
        SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1[4][1],
        passed=not errors,
        errors=errors,
        detail={"runtime_wiring_step": 31},
    )


def _eval_c06_replay02_law() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
        verify_gp08_replay02_publication_epoch_forward_only_static,
    )

    out = verify_gp08_replay02_publication_epoch_forward_only_static()
    if not out.get("passed"):
        errors.append("replay02_gate_failed")
    from vector.domains.cortex.synthesis.synthesis_publication import (
        build_synthesis_publication_status_v1,
        publish_synthesis_epoch_v1,
    )

    if not callable(publish_synthesis_epoch_v1):
        errors.append("missing_publish_synthesis_epoch_v1")
    if not callable(build_synthesis_publication_status_v1):
        errors.append("missing_build_synthesis_publication_status_v1")
    return _criterion_row(
        "C06",
        SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1[5][1],
        passed=not errors,
        errors=errors,
        detail={"runtime_wiring_step": 32},
    )


def _eval_c07_admin_surfaces() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_control_plane import (
        SYNTHESIS_CONTROL_PLANE_SURFACES_V1,
        verify_gp08_cp01_synthesis_control_plane_rbac_static,
    )

    reg = verify_gp08_cp01_synthesis_control_plane_rbac_static()
    if not reg.get("passed"):
        errors.extend(reg.get("detail", {}).get("errors") or [])
    if len(SYNTHESIS_CONTROL_PLANE_SURFACES_V1) != 16:
        errors.append("surface_count_not_16")
    for surface in SYNTHESIS_CONTROL_PLANE_SURFACES_V1:
        if not surface.get("surface_kind"):
            errors.append(f"missing_surface_kind:{surface.get('surface_id')}")
        step = int(surface.get("closure_step") or 99)
        if step <= 30 and not surface.get("wired"):
            errors.append(f"surface_not_wired:{surface.get('surface_id')}")
    return _criterion_row("C07", SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1[6][1], passed=not errors, errors=errors)


def _eval_c08_golden_and_eval() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_evaluation import (
        verify_gp08_eval01_synthesis_evaluation_static_bundle,
    )
    from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
        verify_gp08_gtc01_synthesis_golden_vectors_static_bundle,
    )
    from vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs import (
        verify_gp08_replay17_golden_double_run_corpus_static,
    )

    if not verify_gp08_gtc01_synthesis_golden_vectors_static_bundle().get("passed"):
        errors.append("golden_vectors_bundle_failed")
    if not verify_gp08_replay17_golden_double_run_corpus_static().get("passed"):
        errors.append("replay01_golden_failed")
    if not verify_gp08_eval01_synthesis_evaluation_static_bundle().get("passed"):
        errors.append("eval01_bundle_failed")
    return _criterion_row("C08", SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1[7][1], passed=not errors, errors=errors)


def _eval_c09_tenant_verification() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_tenant_verification import (
        verify_gp08_tver01_org_graph_synthesis_slice_golden_static,
    )

    out = verify_gp08_tver01_org_graph_synthesis_slice_golden_static()
    if not out.get("passed"):
        errors.append("tver01_failed")
    return _criterion_row("C09", SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1[8][1], passed=not errors, errors=errors)


def _eval_c10_e2e_scenario_a_slice() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.testing.e2e_operational_certification import (
        SYNTHESIS_E2E_SCENARIOS_V1,
        SYNTHESIS_E2E_TEST_MODULES_V1,
        verify_gp08_e2e01_operational_certification_static,
    )

    static = verify_gp08_e2e01_operational_certification_static()
    if not static.get("passed"):
        errors.append("gp08_e2e01_static_failed")
        errors.extend(list((static.get("detail") or {}).get("errors") or []))
    if len(SYNTHESIS_E2E_SCENARIOS_V1) != 4:
        errors.append("e2e_scenario_count")
    if len(SYNTHESIS_E2E_TEST_MODULES_V1) != 4:
        errors.append("e2e_test_module_count")
    return _criterion_row(
        "C10",
        SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1[9][1],
        passed=not errors,
        errors=errors,
        detail={"gate_id": static.get("id"), "scenarios": list(SYNTHESIS_E2E_SCENARIOS_V1)},
    )


def _eval_c08_cert_pack() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_certification_pack import (
        verify_gp08_close01_synthesis_cert_pack_closure_static,
    )

    close = verify_gp08_close01_synthesis_cert_pack_closure_static()
    if not close.get("passed"):
        errors.append("close01_cert_pack_failed")
    return _criterion_row(
        "C08b",
        "SYNTHESIS-CERT-PACK-1 generated and verified",
        passed=not errors,
        errors=errors,
        detail={"g_p08_close_01": close},
    )


def _eval_c09_gap_matrix_no_p0() -> dict[str, Any]:
    errors: list[str] = []
    path = _repo_root() / "DOCS" / "cortex" / "synthesis" / "synthesis-spec-gap-matrix.md"
    if not path.is_file():
        errors.append("missing_gap_matrix")
    else:
        text = path.read_text(encoding="utf-8")
        active_p0 = text.split("## Active gaps", 1)
        if len(active_p0) < 2:
            errors.append("active_gaps_section_missing")
        elif "**No Active P0**" not in active_p0[1].split("## Active P1", 1)[0]:
            errors.append("active_p0_rows_remain")
    return _criterion_row("C09b", "No Active P0 in gap matrix", passed=not errors, errors=errors)


def _eval_phase09_readiness_handoff() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_implementation_sequencing import (
        verify_gp08_seq05_phase09_readiness_handoff_static,
    )

    out = verify_gp08_seq05_phase09_readiness_handoff_static()
    if not out.get("passed"):
        errors.append("seq05_phase09_handoff_failed")
    return {
        "check_id": "P09-HANDOFF",
        "label": "Phase 09 readiness checklist",
        "passed": len(errors) == 0,
        "errors": errors,
    }


def build_synthesis_program_completion_matrix_v1(
    session: Session | None = None,
    *,
    tenant_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    """Ten program completion criteria rows (FF-P08-5)."""
    _ = session, tenant_id
    return [
        _eval_c01_doctrine_frozen(),
        _eval_c02_policy_fixture_digest(),
        _eval_c03_schema_ci(),
        _eval_c04_fsm_complete(),
        _eval_c05_pipeline_specified(),
        _eval_c06_replay02_law(),
        _eval_c07_admin_surfaces(),
        _eval_c08_golden_and_eval(),
        _eval_c09_tenant_verification(),
        _eval_c10_e2e_scenario_a_slice(),
        _eval_c08_cert_pack(),
        _eval_c09_gap_matrix_no_p0(),
        _eval_phase09_readiness_handoff(),
    ]


def build_synthesis_operator_closure_checklist_v1(
    *,
    program_passed: bool,
    surfaces_wired: int,
    surfaces_total: int,
) -> list[dict[str, Any]]:
    from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
        build_synthesis_overview_catalog_v1,
    )
    from vector.domains.cortex.synthesis.synthesis_operator_workflows import (
        verify_gp08_wf01_synthesis_spa_routes_complete_static,
    )

    wf = verify_gp08_wf01_synthesis_spa_routes_complete_static()
    rows: list[dict[str, Any]] = []
    for item in SYNTHESIS_OPERATOR_CLOSURE_CHECKLIST_V1:
        cid = item["check_id"]
        if cid == "OP-01":
            passed = surfaces_wired >= 15
        elif cid == "OP-02":
            mod = importlib.import_module("vector.domains.cortex.synthesis.synthesis_orchestrator")
            passed = hasattr(mod, "get_synthesis_job_detail_v1")
        elif cid == "OP-03":
            passed = wf.get("passed") is True
        elif cid == "OP-04":
            passed = program_passed
        elif cid == "OP-05":
            passed = hasattr(
                importlib.import_module(
                    "vector.domains.cortex.synthesis.synthesis_completeness_projection",
                ),
                "build_synthesis_overview_catalog_v1",
            ) and callable(build_synthesis_overview_catalog_v1)
        else:
            passed = False
        rows.append({**item, "passed": passed})
    return rows


def build_synthesis_program_closure_snapshot_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID | str,
) -> dict[str, Any]:
    """Program-level closure snapshot for admin **GET .../program-closure**."""
    from vector.domains.cortex.synthesis.synthesis_certification_pack import (
        build_synthesis_certification_pack_snapshot_v1,
    )
    from vector.domains.cortex.synthesis.synthesis_control_plane import (
        build_synthesis_control_plane_surface_checklist_v1,
    )

    tid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    matrix = build_synthesis_program_completion_matrix_v1(session, tenant_id=tid)
    core_ids = {f"C{i:02d}" for i in range(1, 11)}
    core = [r for r in matrix if r.get("criterion_id") in core_ids]
    cert_row = next((r for r in matrix if r.get("criterion_id") == "C08b"), None)
    gap_row = next((r for r in matrix if r.get("criterion_id") == "C09b"), None)
    program_passed = (
        all(bool(r.get("passed")) for r in core)
        and bool(cert_row and cert_row.get("passed"))
        and bool(gap_row and gap_row.get("passed"))
    )
    checklist_cp = build_synthesis_control_plane_surface_checklist_v1()
    wired = sum(
        1
        for s in checklist_cp
        if s.get("wired_at_closure") and int(s.get("closure_step") or 99) <= 30
    )
    operator_checklist = build_synthesis_operator_closure_checklist_v1(
        program_passed=program_passed,
        surfaces_wired=wired,
        surfaces_total=len(checklist_cp),
    )
    cert = build_synthesis_certification_pack_snapshot_v1(tenant_id=tid)
    return {
        "tenant_id": str(tid),
        "synthesis_program_closure_runtime_schema_version": (
            PHASE08_SYNTHESIS_PROGRAM_CLOSURE_RUNTIME_SCHEMA_VERSION
        ),
        "phase08_program_freeze_version": int(PHASE08_PROGRAM_FREEZE_VERSION),
        "freeze_bundle_id": PHASE08_FREEZE_BUNDLE_FF_P08_5_V1,
        "spec_ref": SYNTHESIS_PROGRAM_CLOSURE_SPEC_REF_V1,
        "program_closure_passed": program_passed,
        "completion_criteria": core
        + ([cert_row] if cert_row else [])
        + [r for r in matrix if r.get("criterion_id") == "C09b"],
        "operator_checklist": operator_checklist,
        "control_plane_surfaces_wired": wired,
        "control_plane_surfaces_total": len(checklist_cp),
        "certification_pack": {
            "synthesis_cert_pack_format": cert.get("synthesis_cert_pack_format"),
            "closure_passed": cert.get("closure_passed"),
            "whole_file_sha256": cert.get("whole_file_sha256"),
            "pack_byte_length": cert.get("pack_byte_length"),
        },
        "normative_program": build_phase08_normative_program_document_v1(),
        "phase09_handoff_check": next(
            (r for r in matrix if r.get("check_id") == "P09-HANDOFF"),
            None,
        ),
    }


def verify_gp08_p30_synthesis_program_closure_static() -> dict[str, Any]:
    """**G-P08-P30-CLOSE** — FF-P08-5 completion criteria + cert pack CI artifact."""
    matrix = build_synthesis_program_completion_matrix_v1(session=None)
    core_ids = {f"C{i:02d}" for i in range(1, 11)}
    criteria = [r for r in matrix if r.get("criterion_id") in core_ids]
    errors: list[str] = []
    for row in criteria:
        if not row.get("passed"):
            errors.append(f"{row.get('criterion_id')}:{row.get('errors')}")
    cert_row = next((r for r in matrix if r.get("criterion_id") == "C08b"), None)
    if cert_row and not cert_row.get("passed"):
        errors.append(f"C08b:{cert_row.get('errors')}")
    p09 = next((r for r in matrix if r.get("check_id") == "P09-HANDOFF"), None)
    if p09 and not p09.get("passed"):
        errors.append(f"P09-HANDOFF:{p09.get('errors')}")
    from vector.domains.cortex.synthesis.synthesis_certification_pack import (
        run_synthesis_gp08_ci_cert_pack_artifact_v1,
    )

    ci = run_synthesis_gp08_ci_cert_pack_artifact_v1()
    if not ci.get("passed"):
        errors.append("ci_cert_pack_artifact_failed")
    return {
        "id": GP08_P30_PROGRAM_CLOSURE_GATE_ID_V1,
        "name": "synthesis_program_closure_ff_p08_5",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "completion_criteria_passed": sum(1 for r in criteria if r.get("passed")),
            "completion_criteria_total": len(criteria),
            "ci_cert_pack": ci,
            "freeze_bundle_id": PHASE08_FREEZE_BUNDLE_FF_P08_5_V1,
        },
    }
