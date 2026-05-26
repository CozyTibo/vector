"""Phase 08 Step 35 — constitutional freeze sign-off (**P08-FINAL-FREEZE**).

Locks doctrine + implementation parity after Steps **1–34**; exposes admin freeze banner catalog.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.synthesis.normative import (
    PHASE08_PROGRAM_FREEZE_VERSION,
    PHASE08_STEP_PROGRAM_COUNT,
    build_phase08_normative_program_document_v1,
)

PHASE08_SYNTHESIS_CONSTITUTIONAL_FREEZE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

P08_FINAL_FREEZE_BUNDLE_ID_V1: Final[str] = "P08-FINAL-FREEZE-2026-05-17"

PHASE08_DOCTRINE_FREEZE_STATUS_V1: Final[str] = "Frozen (implementation)"

GP08_FREEZE01_GATE_ID_V1: Final[str] = "G-P08-FREEZE-01"

PHASE08_CONSTITUTIONAL_CHANGELOG_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/PHASE08_CONSTITUTIONAL_CHANGELOG.md"
)

PHASE08_CONSTITUTIONAL_FREEZE_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/catalog/cortex/synthesis/constitutional-freeze",
)

PHASE08_STEP35_TEST_MODULE_V1: Final[str] = "test_phase08_step35_constitutional_freeze.py"

PHASE08_STEP35_ADMIN_TEST_MODULE_V1: Final[str] = (
    "test_admin_cortex_synthesis_step35_constitutional_freeze.py"
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        if (root / "DOCS" / "cortex" / "synthesis" / "phase-08-normative-index.md").is_file():
            return root
    msg = "repo root not found"
    raise FileNotFoundError(msg)


def _tests_tree_root_v1(repo: Path) -> Path:
    flat = repo / "tests"
    nested = repo / "backend" / "tests"
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"pytest tree not found under {repo}"
    raise FileNotFoundError(msg)


def _changelog_contains_final_freeze_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    path = _repo_root() / "DOCS" / "cortex" / "synthesis" / "PHASE08_CONSTITUTIONAL_CHANGELOG.md"
    if not path.is_file():
        return False, ["missing_changelog"]
    text = path.read_text(encoding="utf-8")
    if P08_FINAL_FREEZE_BUNDLE_ID_V1 not in text:
        errors.append("changelog_missing_final_freeze_bundle")
    if "Step 35" not in text and "step 35" not in text.lower():
        errors.append("changelog_missing_step_35_marker")
    return len(errors) == 0, errors


def _gap_matrix_no_active_p0_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    path = _repo_root() / "DOCS" / "cortex" / "synthesis" / "synthesis-spec-gap-matrix.md"
    if not path.is_file():
        return False, ["missing_gap_matrix"]
    text = path.read_text(encoding="utf-8")
    active = text.split("## Active gaps", 1)
    if len(active) < 2:
        errors.append("active_gaps_section_missing")
    elif "**No Active P0**" not in active[1].split("## Active P1", 1)[0]:
        errors.append("active_p0_rows_remain")
    return len(errors) == 0, errors


def build_synthesis_constitutional_freeze_banner_v1() -> dict[str, str]:
    """Operator-facing freeze banner (admin program catalog + constitutional-freeze catalog)."""
    return {
        "status": PHASE08_DOCTRINE_FREEZE_STATUS_V1,
        "bundle_id": P08_FINAL_FREEZE_BUNDLE_ID_V1,
        "headline": "Phase 08 SIL — implementation program frozen",
        "detail": (
            f"Steps 1–{PHASE08_STEP_PROGRAM_COUNT} runtime shipped; "
            "doctrine + implementation parity locked for Phase 09 handoff."
        ),
    }


def build_synthesis_constitutional_freeze_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for ``GET /admin/catalog/cortex/synthesis/constitutional-freeze``."""
    from vector.domains.cortex.synthesis.synthesis_implementation_sequencing import (
        evaluate_synthesis_implementation_wave_v1,
    )

    wave7 = evaluate_synthesis_implementation_wave_v1("7")
    signoff = build_synthesis_constitutional_freeze_signoff_snapshot_v1()
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_constitutional_freeze_v1",
        "phase08_synthesis_constitutional_freeze_runtime_schema_version": (
            PHASE08_SYNTHESIS_CONSTITUTIONAL_FREEZE_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_FREEZE01_GATE_ID_V1,
        "spec_ref": PHASE08_CONSTITUTIONAL_CHANGELOG_REF_V1,
        "constitutional_freeze_bundle": P08_FINAL_FREEZE_BUNDLE_ID_V1,
        "phase08_program_freeze_version": int(PHASE08_PROGRAM_FREEZE_VERSION),
        "step_program_count": int(PHASE08_STEP_PROGRAM_COUNT),
        "doctrine_freeze_status": PHASE08_DOCTRINE_FREEZE_STATUS_V1,
        "freeze_banner": build_synthesis_constitutional_freeze_banner_v1(),
        "wave_7_deliverables_passed": bool(wave7.get("passed")),
        "signoff_passed": bool(signoff.get("constitutional_freeze_passed")),
        "admin_openapi_paths": list(PHASE08_CONSTITUTIONAL_FREEZE_ADMIN_OPENAPI_PATHS_V1),
    }


def build_synthesis_constitutional_freeze_signoff_snapshot_v1() -> dict[str, Any]:
    """Full Step 35 sign-off snapshot (all 10 completion criteria + wave 7 + gates)."""
    from vector.domains.cortex.synthesis.synthesis_implementation_sequencing import (
        build_synthesis_phase09_readiness_checklist_v1,
        evaluate_synthesis_implementation_wave_v1,
    )
    from vector.domains.cortex.synthesis.synthesis_program_closure import (
        build_synthesis_program_completion_matrix_v1,
    )

    matrix = build_synthesis_program_completion_matrix_v1(session=None)
    core_ids = {f"C{i:02d}" for i in range(1, 11)}
    core = [r for r in matrix if r.get("criterion_id") in core_ids]
    cert_row = next((r for r in matrix if r.get("criterion_id") == "C08b"), None)
    gap_row = next((r for r in matrix if r.get("criterion_id") == "C09b"), None)
    p09_row = next((r for r in matrix if r.get("check_id") == "P09-HANDOFF"), None)

    core_passed = all(bool(r.get("passed")) for r in core)
    cert_passed = bool(cert_row and cert_row.get("passed"))
    gap_passed = bool(gap_row and gap_row.get("passed"))
    p09_passed = bool(p09_row and p09_row.get("passed"))

    changelog_ok, changelog_errors = _changelog_contains_final_freeze_v1()
    gap_doc_ok, gap_doc_errors = _gap_matrix_no_active_p0_v1()
    wave7 = evaluate_synthesis_implementation_wave_v1("7")

    passed = (
        core_passed
        and cert_passed
        and gap_passed
        and p09_passed
        and changelog_ok
        and gap_doc_ok
        and bool(wave7.get("passed"))
    )
    gate = verify_gp08_freeze01_constitutional_freeze_static()
    passed = passed and bool(gate.get("passed"))
    return {
        "constitutional_freeze_bundle": P08_FINAL_FREEZE_BUNDLE_ID_V1,
        "doctrine_freeze_status": PHASE08_DOCTRINE_FREEZE_STATUS_V1,
        "phase08_program_freeze_version": int(PHASE08_PROGRAM_FREEZE_VERSION),
        "constitutional_freeze_passed": passed,
        "completion_criteria_core": core,
        "cert_pack_criterion": cert_row,
        "gap_matrix_criterion": gap_row,
        "phase09_handoff": p09_row,
        "phase09_readiness_checklist": build_synthesis_phase09_readiness_checklist_v1(),
        "wave_7": wave7,
        "changelog_check": {"passed": changelog_ok, "errors": changelog_errors},
        "gap_matrix_doc_check": {"passed": gap_doc_ok, "errors": gap_doc_errors},
        "gate": gate,
        "freeze_banner": build_synthesis_constitutional_freeze_banner_v1(),
        "normative_program": build_phase08_normative_program_document_v1(),
    }


def verify_gp08_freeze01_constitutional_freeze_static() -> dict[str, Any]:
    """**G-P08-FREEZE-01** — P08-FINAL-FREEZE sign-off (10 criteria + wave 7 + E2E static)."""
    errors: list[str] = []

    changelog_ok, changelog_errors = _changelog_contains_final_freeze_v1()
    if not changelog_ok:
        errors.extend(changelog_errors)

    gap_ok, gap_errors = _gap_matrix_no_active_p0_v1()
    if not gap_ok:
        errors.extend(gap_errors)

    from vector.domains.cortex.synthesis.synthesis_program_closure import (
        verify_gp08_p30_synthesis_program_closure_static,
    )

    p30 = verify_gp08_p30_synthesis_program_closure_static()
    if not p30.get("passed"):
        errors.append("p30_program_closure_failed")
        errors.extend(list((p30.get("detail") or {}).get("errors") or []))

    from vector.domains.cortex.synthesis.testing.e2e_operational_certification import (
        verify_gp08_e2e01_operational_certification_static,
    )

    e2e = verify_gp08_e2e01_operational_certification_static()
    if not e2e.get("passed"):
        errors.append("e2e01_failed")

    from vector.domains.cortex.synthesis.synthesis_implementation_sequencing import (
        evaluate_synthesis_implementation_wave_v1,
        verify_gp08_seq06_wave_seven_complete_static,
    )

    wave7 = evaluate_synthesis_implementation_wave_v1("7")
    if not wave7.get("passed"):
        for d in wave7.get("deliverables") or []:
            if not d.get("passed"):
                errors.append(f"wave7:{d.get('deliverable_id')}")

    seq06 = verify_gp08_seq06_wave_seven_complete_static()
    if not seq06.get("passed"):
        errors.append("seq06_wave_7_failed")

    repo = _repo_root()
    tests_root = _tests_tree_root_v1(repo)
    synth_tests = tests_root / "vector" / "domains" / "cortex" / "synthesis"
    step35 = synth_tests / PHASE08_STEP35_TEST_MODULE_V1
    if not step35.is_file():
        errors.append(f"missing:{PHASE08_STEP35_TEST_MODULE_V1}")

    step_tests = list(synth_tests.glob("test_phase08_step*.py"))
    if len(step_tests) < 30:
        errors.append(f"step_test_module_count_low:{len(step_tests)}")
    for step in (30, 31, 32, 33, 34, 35):
        prefix = f"test_phase08_step{step:02d}_"
        if not list(synth_tests.glob(f"{prefix}*.py")):
            errors.append(f"missing_step_tests:step_{step}")

    return {
        "id": GP08_FREEZE01_GATE_ID_V1,
        "name": "gp08_freeze01_constitutional_freeze",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "bundle_id": P08_FINAL_FREEZE_BUNDLE_ID_V1,
            "doctrine_freeze_status": PHASE08_DOCTRINE_FREEZE_STATUS_V1,
            "p30_closure": p30.get("passed"),
        },
    }
