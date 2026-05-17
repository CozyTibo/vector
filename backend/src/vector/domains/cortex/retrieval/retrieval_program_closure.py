"""Phase 07 P07-30 — program closure + **FF-P07-5** admin freeze.

Normative: ``DOCS/cortex/retrieval/phase-07-closure-gates-doctrine.md`` (10 completion criteria,
**G-P07-CLOSE-01** program gate, operator checklist).
"""

from __future__ import annotations

import importlib
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import (
    PHASE07_FREEZE_BUNDLE_IDS,
    PHASE07_PROGRAM_FREEZE_VERSION,
    PHASE07_STEP_PROGRAM_COUNT,
    build_phase07_normative_program_document_v1,
)

PHASE07_RETRIEVAL_PROGRAM_CLOSURE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_PROGRAM_CLOSURE_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-closure-gates-doctrine.md"
)

PHASE07_FREEZE_BUNDLE_FF_P07_5_V1: Final[str] = "FF-P07-5"

GP07_P30_PROGRAM_CLOSURE_GATE_ID_V1: Final[str] = "G-P07-P30-CLOSE"

RETRIEVAL_PROGRAM_CLOSURE_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/retrieval/program-closure",
)

_PHASE07_REQUIRED_DOCTRINE_FILES_V1: Final[tuple[str, ...]] = (
    "PHASE07_CONSTITUTIONAL_CHANGELOG.md",
    "phase-07-normative-index.md",
    "phase-07-closure-gates-doctrine.md",
    "phase-07-implementation-sequencing-plan.md",
    "phase-07-verification-harness-spec.md",
    "retrieval-spec-gap-matrix.md",
)

RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1: Final[tuple[tuple[str, str], ...]] = (
    ("C01", "Steps 1-30 doctrine frozen"),
    ("C02", "All hard_fail G-P07-* gates wired in CI"),
    ("C03", "Admin surfaces 1-16 shipped"),
    ("C04", "Substrate completeness retrieval stage live"),
    ("C05", "Index publish job durable"),
    ("C06", "G-P07-REPLAY-01 pass on golden tenant slice"),
    ("C07", "R-LEG production predicates satisfied"),
    ("C08", "RETRIEVAL-CERT-PACK-1 generated and verified"),
    ("C09", "No Active P0 in gap matrix"),
    ("C10", "Phase 08 handoff signed (boundary + readiness)"),
)

RETRIEVAL_OPERATOR_CLOSURE_CHECKLIST_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "check_id": "OP-01",
        "label": "Retrieval nav tab enabled",
        "detail": "Admin SPA exposes retrieval section with program-closure surface",
    },
    {
        "check_id": "OP-02",
        "label": "Overview integration live",
        "detail": "GET /overview exposes health_strip + completeness for substrate stage",
    },
    {
        "check_id": "OP-03",
        "label": "Dangerous actions policy-gated",
        "detail": "Index rebuild requires EXECUTE RETRIEVAL INDEX REBUILD confirmation (RET-WF-02)",
    },
    {
        "check_id": "OP-04",
        "label": "Operator verification checklist",
        "detail": "GET /program-closure exposes completion matrix + cert pack digest",
    },
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        if (root / "DOCS" / "cortex" / "retrieval" / "phase-07-normative-index.md").is_file():
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
    retrieval_dir = root / "DOCS" / "cortex" / "retrieval"
    for name in _PHASE07_REQUIRED_DOCTRINE_FILES_V1:
        if not (retrieval_dir / name).is_file():
            errors.append(f"missing_doctrine:{name}")
    tracker = root / "DOCS" / "cortex" / "MASTER_TRACKER.md"
    if not tracker.is_file():
        errors.append("missing_master_tracker")
    else:
        text = tracker.read_text(encoding="utf-8")
        if "Phase 07" not in text or "| 30 |" not in text:
            errors.append("master_tracker_phase07_incomplete")
    doc = build_phase07_normative_program_document_v1()
    if doc.get("step_program_count") != PHASE07_STEP_PROGRAM_COUNT:
        errors.append("step_program_count_mismatch")
    if PHASE07_FREEZE_BUNDLE_FF_P07_5_V1 not in PHASE07_FREEZE_BUNDLE_IDS:
        errors.append("ff_p07_5_not_in_freeze_bundles")
    return _criterion_row("C01", RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1[0][1], passed=not errors, errors=errors)


def _eval_c02_hard_fail_gates_ci() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.retrieval.retrieval_verification_harness import (
        run_retrieval_gp07_ci_full_wired_stages_with_meta_v1,
        verify_gp07_rvh02_pr_blocking_bundle_passes_static,
    )

    pr = verify_gp07_rvh02_pr_blocking_bundle_passes_static()
    if not pr.get("passed"):
        errors.append("pr_blocking_not_green")
    full = run_retrieval_gp07_ci_full_wired_stages_with_meta_v1(abort_on_hard_fail=False)
    if not full.get("passed"):
        errors.append(f"full_az_failed:{full.get('failed_gate_id')}")
    return _criterion_row(
        "C02",
        RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1[1][1],
        passed=not errors,
        errors=errors,
        detail={"pr_blocking": pr.get("passed"), "full_az": full.get("passed")},
    )


def _eval_c03_admin_surfaces() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.retrieval.retrieval_control_plane import (
        verify_retrieval_control_plane_surface_registry_static,
    )

    reg = verify_retrieval_control_plane_surface_registry_static()
    if not reg.get("passed"):
        errors.extend(reg.get("detail", {}).get("errors") or [])
    return _criterion_row("C03", RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1[2][1], passed=not errors, errors=errors)


def _eval_c04_completeness_stage() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
        build_retrieval_overview_catalog_v1,
        verify_gp07_comp01_never_idle_healthy_static,
    )

    comp = verify_gp07_comp01_never_idle_healthy_static()
    if not comp.get("passed"):
        errors.append("comp01_gate_failed")
    mod = importlib.import_module(
        "vector.domains.cortex.retrieval.retrieval_completeness_projection"
    )
    if not hasattr(mod, "project_retrieval_completeness_v1"):
        errors.append("missing_project_retrieval_completeness_v1")
    if not hasattr(mod, "build_retrieval_overview_catalog_v1"):
        errors.append("missing_build_retrieval_overview_catalog_v1")
    return _criterion_row("C04", RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1[3][1], passed=not errors, errors=errors)


def _eval_c05_index_publish_durable() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        get_published_index_epoch_v1,
        run_retrieval_index_rebuild_v1,
    )

    try:
        importlib.import_module("vector.infrastructure.db.models.cortex_retrieval_index_entry")
        importlib.import_module("vector.infrastructure.db.models.cortex_retrieval_query_audit")
    except ImportError as exc:
        errors.append(f"orm_import_failed:{exc}")
    if not callable(run_retrieval_index_rebuild_v1):
        errors.append("missing_index_rebuild")
    if not callable(get_published_index_epoch_v1):
        errors.append("missing_published_epoch")
    return _criterion_row("C05", RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1[4][1], passed=not errors, errors=errors)


def _eval_c06_replay_golden_slice() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
        verify_gp07_replay_01_canonical_identity_stable_static,
    )
    from vector.domains.cortex.retrieval.retrieval_tenant_verification_slice import (
        verify_gp07_tver01_org_graph_retrieval_slice_golden_static,
    )

    r01 = verify_gp07_replay_01_canonical_identity_stable_static()
    if not r01.get("passed"):
        errors.append("replay01_failed")
    tver = verify_gp07_tver01_org_graph_retrieval_slice_golden_static()
    if not tver.get("passed"):
        errors.append("tver01_golden_slice_failed")
    return _criterion_row(
        "C06",
        RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1[5][1],
        passed=not errors,
        errors=errors,
        detail={"replay01": r01.get("passed"), "tver01": tver.get("passed")},
    )


def _eval_c07_r_leg_production(
    session: Session | None,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.retrieval.retrieval_runtime_legality_matrix import (
        evaluate_retrieval_production_gates_v1,
        verify_gp07_rlm01_retrieval_runtime_legality_matrix_static_bundle,
    )

    rlm = verify_gp07_rlm01_retrieval_runtime_legality_matrix_static_bundle()
    if not rlm.get("passed"):
        errors.append("rlm01_bundle_failed")
    gates = evaluate_retrieval_production_gates_v1(session, tenant_id=tenant_id)
    if session is None:
        for key in ("R-LEG-01", "R-LEG-07"):
            if not gates.get(key, {}).get("passed"):
                errors.append(f"{key}_static_failed")
    else:
        failed = [k for k, v in gates.items() if not v.get("passed")]
        if failed:
            errors.append(f"production_gates_failed:{failed}")
    return _criterion_row(
        "C07",
        RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1[6][1],
        passed=len(errors) == 0,
        errors=errors,
        detail={"production_gates": gates, "rlm01": rlm.get("passed")},
    )


def _eval_c08_cert_pack() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.retrieval.retrieval_certification_pack import (
        verify_gp07_close01_retrieval_cert_pack_closure_static,
    )

    close = verify_gp07_close01_retrieval_cert_pack_closure_static()
    if not close.get("passed"):
        errors.append("close01_cert_pack_failed")
    return _criterion_row(
        "C08",
        RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1[7][1],
        passed=not errors,
        errors=errors,
        detail={"g_p07_close_01": close},
    )


def _eval_c09_gap_matrix_no_p0() -> dict[str, Any]:
    errors: list[str] = []
    path = _repo_root() / "DOCS" / "cortex" / "retrieval" / "retrieval-spec-gap-matrix.md"
    if not path.is_file():
        errors.append("missing_gap_matrix")
    else:
        text = path.read_text(encoding="utf-8")
        active_p0 = text.split("## Active P0", 1)
        if len(active_p0) < 2:
            errors.append("active_p0_section_missing")
        else:
            section = active_p0[1].split("##", 1)[0]
            lines = [
                ln.strip()
                for ln in section.splitlines()
                if ln.strip().startswith("|") and not ln.strip().startswith("| --")
            ]
            data_rows = [
                ln
                for ln in lines
                if not ln.startswith("| ID") and "*none*" not in ln.lower()
            ]
            if data_rows:
                errors.append(f"active_p0_rows_remain:{len(data_rows)}")
    return _criterion_row("C09", RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1[8][1], passed=not errors, errors=errors)


def _eval_c10_phase08_handoff() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.retrieval.phase_boundaries import (
        verify_gp07_bnd08_synthesis_boundary_static,
        verify_gp07_bnd_catalog_static,
    )
    from vector.domains.cortex.retrieval.retrieval_implementation_sequencing import (
        verify_gp07_seq05_phase08_readiness_handoff_static,
    )

    for fn in (
        verify_gp07_bnd08_synthesis_boundary_static,
        verify_gp07_bnd_catalog_static,
        verify_gp07_seq05_phase08_readiness_handoff_static,
    ):
        out = fn()
        if not out.get("passed"):
            errors.append(f"{out.get('id')}_failed")
    return _criterion_row("C10", RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1[9][1], passed=not errors, errors=errors)


def _eval_rd_topology_complete() -> dict[str, Any]:
    """Extra closure invariant: all ``RD-*`` codes appear in degradation topology."""
    errors: list[str] = []
    from vector.domains.cortex.retrieval.retrieval_bounded_caps import RETRIEVAL_RD_CODES_REGISTRY_V1
    from vector.domains.cortex.retrieval.retrieval_degradation_taxonomy import (
        build_retrieval_degradation_topology_catalog_v1,
        verify_gp07_deg03_propagation_table_static,
    )

    if not verify_gp07_deg03_propagation_table_static().get("passed"):
        errors.append("deg03_propagation_failed")
    topo = build_retrieval_degradation_topology_catalog_v1()
    reg = frozenset(topo.get("rd_codes_registry") or [])
    if reg != RETRIEVAL_RD_CODES_REGISTRY_V1:
        missing = sorted(RETRIEVAL_RD_CODES_REGISTRY_V1 - reg)
        extra = sorted(reg - RETRIEVAL_RD_CODES_REGISTRY_V1)
        if missing:
            errors.append(f"topology_missing_rd:{missing}")
        if extra:
            errors.append(f"topology_extra_rd:{extra}")
    return {
        "check_id": "RD-TOPOLOGY",
        "label": "All RD-* codes in degradation topology",
        "passed": len(errors) == 0,
        "errors": errors,
    }


def build_retrieval_program_completion_matrix_v1(
    session: Session | None = None,
    *,
    tenant_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    """Ten program completion criteria rows (doctrine § Phase completion criteria)."""
    tid = tenant_id or uuid.UUID(int=0)
    return [
        _eval_c01_doctrine_frozen(),
        _eval_c02_hard_fail_gates_ci(),
        _eval_c03_admin_surfaces(),
        _eval_c04_completeness_stage(),
        _eval_c05_index_publish_durable(),
        _eval_c06_replay_golden_slice(),
        _eval_c07_r_leg_production(session, tenant_id=tid),
        _eval_c08_cert_pack(),
        _eval_c09_gap_matrix_no_p0(),
        _eval_c10_phase08_handoff(),
        _eval_rd_topology_complete(),
    ]


def build_retrieval_operator_closure_checklist_v1(
    *,
    program_passed: bool,
    surfaces_wired: int,
    surfaces_total: int,
) -> list[dict[str, Any]]:
    """Operator checklist rows for admin UI (doctrine § Admin closure)."""
    from vector.domains.cortex.retrieval.retrieval_operator_workflows import (
        verify_gp07_wf01_spa_routes_complete_static,
    )

    wf = verify_gp07_wf01_spa_routes_complete_static()
    rows: list[dict[str, Any]] = []
    for item in RETRIEVAL_OPERATOR_CLOSURE_CHECKLIST_V1:
        cid = item["check_id"]
        if cid == "OP-01":
            passed = surfaces_wired == surfaces_total == 16
        elif cid == "OP-02":
            mod = importlib.import_module(
                "vector.domains.cortex.retrieval.retrieval_completeness_projection"
            )
            passed = hasattr(mod, "build_retrieval_overview_catalog_v1")
        elif cid == "OP-03":
            passed = wf.get("passed") is True
        elif cid == "OP-04":
            passed = program_passed
        else:
            passed = False
        rows.append({**item, "passed": passed})
    return rows


def build_retrieval_program_closure_snapshot_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID | str,
) -> dict[str, Any]:
    """Program-level closure snapshot for admin **GET .../program-closure**."""
    from vector.domains.cortex.retrieval.retrieval_certification_pack import (
        build_retrieval_certification_pack_snapshot_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_control_plane import (
        build_retrieval_control_plane_surface_checklist_v1,
    )

    tid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    matrix = build_retrieval_program_completion_matrix_v1(session, tenant_id=tid)
    criteria = [r for r in matrix if r.get("criterion_id", "").startswith("C")]
    program_passed = all(bool(r.get("passed")) for r in criteria)
    checklist_cp = build_retrieval_control_plane_surface_checklist_v1()
    wired = sum(1 for s in checklist_cp if s.get("wired_at_closure"))
    operator_checklist = build_retrieval_operator_closure_checklist_v1(
        program_passed=program_passed,
        surfaces_wired=wired,
        surfaces_total=len(checklist_cp),
    )
    cert = build_retrieval_certification_pack_snapshot_v1(tenant_id=tid)
    return {
        "tenant_id": str(tid),
        "retrieval_program_closure_runtime_schema_version": (
            PHASE07_RETRIEVAL_PROGRAM_CLOSURE_RUNTIME_SCHEMA_VERSION
        ),
        "retrieval_program_freeze_version": int(PHASE07_PROGRAM_FREEZE_VERSION),
        "freeze_bundle_id": PHASE07_FREEZE_BUNDLE_FF_P07_5_V1,
        "spec_ref": RETRIEVAL_PROGRAM_CLOSURE_SPEC_REF_V1,
        "program_closure_passed": program_passed,
        "completion_criteria": criteria,
        "rd_topology_check": next(
            (r for r in matrix if r.get("check_id") == "RD-TOPOLOGY"),
            None,
        ),
        "operator_checklist": operator_checklist,
        "control_plane_surfaces_wired": wired,
        "control_plane_surfaces_total": len(checklist_cp),
        "certification_pack": {
            "retrieval_cert_pack_format": cert.get("retrieval_cert_pack_format"),
            "closure_passed": cert.get("closure_passed"),
            "whole_file_sha256": cert.get("whole_file_sha256"),
            "pack_byte_length": cert.get("pack_byte_length"),
        },
        "normative_program": build_phase07_normative_program_document_v1(),
    }


def run_retrieval_gp07_ci_cert_pack_artifact_v1() -> dict[str, Any]:
    """CI entry: build + verify **RETRIEVAL-CERT-PACK-1** (Step 30 / doctrine § criterion 8)."""
    from vector.domains.cortex.retrieval.retrieval_certification_pack import (
        RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
        _run_closure_pipeline_build_pack_v1,
        verify_retrieval_cert_pack_v1,
    )

    ok, detail, pack = _run_closure_pipeline_build_pack_v1()
    verify_passed = False
    if pack is not None:
        verify_passed = verify_retrieval_cert_pack_v1(pack).passed
    return {
        "passed": bool(ok and verify_passed),
        "retrieval_cert_pack_format": RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
        "pack_bytes": len(pack) if pack else 0,
        "build_detail": detail,
        "verify_passed": verify_passed,
    }


def verify_gp07_p30_retrieval_program_closure_static() -> dict[str, Any]:
    """**G-P07-P30-CLOSE** — all ten completion criteria + cert pack CI artifact green."""
    matrix = build_retrieval_program_completion_matrix_v1(session=None)
    criteria = [r for r in matrix if str(r.get("criterion_id", "")).startswith("C")]
    errors: list[str] = []
    for row in criteria:
        if not row.get("passed"):
            errors.append(f"{row.get('criterion_id')}:{row.get('errors')}")
    rd = next((r for r in matrix if r.get("check_id") == "RD-TOPOLOGY"), None)
    if rd and not rd.get("passed"):
        errors.append(f"RD-TOPOLOGY:{rd.get('errors')}")
    ci = run_retrieval_gp07_ci_cert_pack_artifact_v1()
    if not ci.get("passed"):
        errors.append("ci_cert_pack_artifact_failed")
    return {
        "id": GP07_P30_PROGRAM_CLOSURE_GATE_ID_V1,
        "name": "retrieval_program_closure_ff_p07_5",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "completion_criteria_passed": sum(1 for r in criteria if r.get("passed")),
            "completion_criteria_total": len(criteria),
            "ci_cert_pack": ci,
            "freeze_bundle_id": PHASE07_FREEZE_BUNDLE_FF_P07_5_V1,
        },
    }
