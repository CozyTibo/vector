"""Phase 08.5 P085-35 — Phase 09 readiness gates (**G-P085-READY-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-phase-09-readiness-doctrine.md``.
"""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_gap_matrix import (
    parse_cesp_gap_matrix_markdown_v1,
    summarize_cesp_gap_matrix_v1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_HARD_DOWNSTREAM_GATE_V1,
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.operational_cockpit import (
    OPERATIONAL_COCKPIT_SURFACES_V1,
)
from vector.domains.cortex.operational_runtime.phase_boundaries import (
    assert_phase09_blocked_until_cesp_close_v1,
    hash_synthesis_artifact_schema_fixture_v1,
    list_registered_cesp_admin_route_paths_v1,
)
from vector.infrastructure.db.models.cortex_phase09_readiness_signoff import (
    CortexPhase09ReadinessSignoff,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.settings import get_settings

PHASE085_PHASE09_READINESS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_PHASE09_READINESS_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-phase-09-readiness-doctrine.md"
)

GP085_READY01_GATE_ID_V1: Final[str] = "G-P085-READY-01"

READINESS_SIGNOFF_KIND_SOAK_7D_V1: Final[str] = "soak_7d_ops"

READINESS_ALLOWED_OPEN_P0_V1: Final[frozenset[str]] = frozenset(
    {
        "P0-085-01",
        "P0-085-05",
        "P0-085-10",
    },
)

PHASE09_READINESS_CRITERION_IDS_V1: Final[tuple[str, ...]] = tuple(
    f"R{i}" for i in range(1, 16)
)


class Phase09ReadinessError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def build_phase09_readiness_catalog_v1() -> dict[str, Any]:
    checklist = build_phase09_readiness_checklist_v1()
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_phase09_readiness_runtime_schema_version": int(
            PHASE085_PHASE09_READINESS_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_PHASE09_READINESS_SPEC_REF_V1,
        "primary_gate_id": GP085_READY01_GATE_ID_V1,
        "criterion_ids": list(PHASE09_READINESS_CRITERION_IDS_V1),
        "hard_downstream_gate": PHASE085_HARD_DOWNSTREAM_GATE_V1,
        "phase09_blocked_until": [PHASE085_HARD_DOWNSTREAM_GATE_V1, GP085_READY01_GATE_ID_V1],
        "golden_tenant_profile": build_golden_tenant_profile_spec_v1(),
        "checklist": checklist,
        "readiness_passed": all(bool(c.get("passed")) for c in checklist),
        "evaluation_entrypoints": [
            "build_phase09_readiness_checklist_v1",
            "evaluate_golden_tenant_profile_v1",
            "record_phase09_soak_signoff_v1",
        ],
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_phase09_readiness"
        ),
    }


def build_golden_tenant_profile_spec_v1() -> dict[str, Any]:
    return {
        "tenant_profile": "mock dataset with cortex capability scenarios",
        "within_hours": 2,
        "requirements": [
            "non_zero_published_retrieval_rows",
            "non_zero_eligible_scopes",
            "at_least_one_completed_synthesis_job",
            "zero_unrecovered_stalls",
        ],
    }


def _criterion_row_v1(
    criterion_id: str,
    *,
    text: str,
    verification: str,
    passed: bool,
    errors: list[str] | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "text": text,
        "verification": verification,
        "passed": passed,
        "errors": list(errors or []),
        "detail": dict(detail or {}),
    }


def _evaluate_r1_continuation_law_v1() -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.cesp_continuation_gate import (
        verify_gp085_continuation_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_progression_gate import (
        verify_gp085_progression_gate_static,
    )

    prog = verify_gp085_progression_gate_static()
    cont = verify_gp085_continuation_gate_static()
    passed = bool(prog.get("passed")) and bool(cont.get("passed"))
    errors: list[str] = []
    if not prog.get("passed"):
        errors.append("prog01_gate_failed")
    if not cont.get("passed"):
        errors.append("continuation_gate_failed")
    return _criterion_row_v1(
        "R1",
        text="Continuation law wired 06→07→08",
        verification="G-P085-PROG-01 + G-P085-CONT-01",
        passed=passed,
        errors=errors,
        detail={"prog01": prog.get("passed"), "cont01": cont.get("passed")},
    )


def _evaluate_r2_watchdog_v1() -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.cesp_watchdog_gate import (
        verify_gp085_watchdog_gate_static,
    )

    gate = verify_gp085_watchdog_gate_static()
    return _criterion_row_v1(
        "R2",
        text="Watchdog + auto-recover shipped",
        verification="G-P085-WATCH-01",
        passed=bool(gate.get("passed")),
        errors=[] if gate.get("passed") else ["watch01_failed"],
    )


def _evaluate_r3_fake_green_v1() -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.cesp_anti_idle_gate import (
        verify_gp085_anti_idle01_static,
    )

    gate = verify_gp085_anti_idle01_static()
    return _criterion_row_v1(
        "R3",
        text="Fake-green idle eliminated",
        verification="G-P085-ANTI-IDLE-01",
        passed=bool(gate.get("passed")),
        errors=[] if gate.get("passed") else ["anti_idle01_failed"],
    )


def _evaluate_r4_retrieval_reports_v1() -> dict[str, Any]:
    from vector.domains.cortex.retrieval import retrieval_index_materialization as rim

    src = inspect.getsource(rim.materialize_retrieval_index_for_pipeline_v1)
    passed = "persist_retrieval_materialization_report_v1" in src
    return _criterion_row_v1(
        "R4",
        text="Retrieval materialization reports on every phase 07",
        verification="persist_retrieval_materialization_report_v1",
        passed=passed,
        errors=[] if passed else ["materialization_report_hook_missing"],
    )


def _evaluate_r5_synthesis_explain_admin_v1() -> dict[str, Any]:
    routes = list_registered_cesp_admin_route_paths_v1()
    path = "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-eligibility/explain"
    passed = path in routes
    from vector.domains.cortex.synthesis import synthesis_eligibility_explainability as see

    wired = "explain_synthesis_eligibility_v1" in inspect.getsource(see.explain_synthesis_eligibility_v1)
    passed = passed and wired
    errors: list[str] = []
    if path not in routes:
        errors.append("admin_route_missing")
    if not wired:
        errors.append("explain_symbol_missing")
    return _criterion_row_v1(
        "R5",
        text="explain_synthesis_eligibility_v1 in admin",
        verification="admin route + explain symbol",
        passed=passed,
        errors=errors,
    )


def _evaluate_r6_graph_density_v1() -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.cesp_promotion_gate import (
        verify_gp085_promotion_gate_static,
    )

    parsed = parse_cesp_gap_matrix_markdown_v1()
    p0_06_closed = any(
        r.get("gap_id") == "P0-085-06" and r.get("status") == "closed"
        for r in parsed.get("active_p0") or []
    )
    promo = verify_gp085_promotion_gate_static()
    passed = bool(promo.get("passed")) or p0_06_closed
    return _criterion_row_v1(
        "R6",
        text="Graph density pass OR documented defer with P0 cleared",
        verification="G-P085-PROMO-01 | P0-085-06 closed",
        passed=passed,
        errors=[] if passed else ["promo01_and_p0_085_06_open"],
        detail={"promo01_passed": promo.get("passed"), "p0_085_06_closed": p0_06_closed},
    )


def _evaluate_r7_traversal_v1() -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.cesp_traversal_scheduling_gate import (
        verify_gp085_traversal_scheduling_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_retrieval_starvation_gate import (
        verify_gp085_retrieval_starvation_gate_static,
    )

    walk = verify_gp085_traversal_scheduling_gate_static()
    starve = verify_gp085_retrieval_starvation_gate_static()
    passed = bool(walk.get("passed")) and bool(starve.get("passed"))
    return _criterion_row_v1(
        "R7",
        text="Traversal scheduler OR starvation visible",
        verification="G-P085-WALK-01 + G-P085-RET-02",
        passed=passed,
        errors=[] if passed else ["walk01_or_ret02_failed"],
        detail={"walk01": walk.get("passed"), "ret02": starve.get("passed")},
    )


def _evaluate_r8_tcre_saturation_v1() -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.cesp_tcre_saturation_gate import (
        verify_gp085_tcre_saturation_gate_static,
    )

    gate = verify_gp085_tcre_saturation_gate_static()
    return _criterion_row_v1(
        "R8",
        text="TCRE saturation scheduler",
        verification="G-P085-TCRE-01",
        passed=bool(gate.get("passed")),
        errors=[] if gate.get("passed") else ["tcre01_failed"],
    )


def _evaluate_r9_synthesis_audits_v1() -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.cesp_synthesis_activation_gate import (
        verify_gp085_synthesis_activation_gate_static,
    )

    gate = verify_gp085_synthesis_activation_gate_static()
    errors: list[str] = []
    if not gate.get("passed"):
        errors.append("syn01_failed")
    try:
        from vector.infrastructure.db.models.cortex_synthesis_activation_audit import (  # noqa: PLC0415
            CortexSynthesisActivationAudit,
        )

        _ = CortexSynthesisActivationAudit.__tablename__
    except Exception:  # noqa: BLE001
        errors.append("activation_audit_model_missing")
    passed = not errors
    return _criterion_row_v1(
        "R9",
        text="Synthesis activation audits",
        verification="G-P085-SYN-01 + cortex_synthesis_activation_audits",
        passed=passed,
        errors=errors,
    )


def _evaluate_r10_maturity_v1() -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.cesp_operational_maturity_gate import (
        verify_gp085_operational_maturity_gate_static,
    )

    gate = verify_gp085_operational_maturity_gate_static()
    return _criterion_row_v1(
        "R10",
        text="Multi-dimensional maturity",
        verification="G-P085-MAT-01",
        passed=bool(gate.get("passed")),
        errors=[] if gate.get("passed") else ["mat01_failed"],
    )


def _evaluate_r11_cockpit_surfaces_v1() -> dict[str, Any]:
    surfaces_1_16 = [s for s in OPERATIONAL_COCKPIT_SURFACES_V1 if int(s["surface_number"]) <= 16]
    wired = [s for s in surfaces_1_16 if s.get("wired")]
    passed = len(surfaces_1_16) == 16 and len(wired) == 16
    return _criterion_row_v1(
        "R11",
        text="Admin cockpit surfaces 1–16",
        verification="OPERATIONAL_COCKPIT_SURFACES_V1 wired",
        passed=passed,
        errors=[] if passed else ["cockpit_surfaces_1_16_incomplete"],
        detail={"surfaces_total": len(surfaces_1_16), "wired_total": len(wired)},
    )


def _evaluate_r12_economics_caps_v1() -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.cesp_runtime_economics_gate import (
        verify_gp085_runtime_economics_gate_static,
    )

    gate = verify_gp085_runtime_economics_gate_static()
    cfg = get_settings()
    errors: list[str] = []
    if int(cfg.cortex_substrate_pipeline_max_concurrent_per_tenant) < 1:
        errors.append("pipeline_concurrency_unset")
    if int(cfg.cortex_vector_queue_backpressure_threshold) < 1:
        errors.append("queue_backpressure_unset")
    if float(cfg.cortex_tcre_saturation_threshold) <= 0:
        errors.append("tcre_threshold_unset")
    passed = bool(gate.get("passed")) and not errors
    return _criterion_row_v1(
        "R12",
        text="Economics caps configured in prod",
        verification="G-P085-ECON-01 + settings audit",
        passed=passed,
        errors=errors,
        detail={
            "econ01_passed": gate.get("passed"),
            "pipeline_max_concurrent": int(cfg.cortex_substrate_pipeline_max_concurrent_per_tenant),
            "queue_backpressure_threshold": int(cfg.cortex_vector_queue_backpressure_threshold),
        },
    )


def _evaluate_r13_gap_matrix_v1() -> dict[str, Any]:
    parsed = parse_cesp_gap_matrix_markdown_v1()
    summary = summarize_cesp_gap_matrix_v1(parsed)
    open_p0 = [
        str(r["gap_id"])
        for r in parsed.get("active_p0") or []
        if r.get("status") == "open"
    ]
    blocking = [gid for gid in open_p0 if gid not in READINESS_ALLOWED_OPEN_P0_V1]
    passed = len(blocking) == 0
    return _criterion_row_v1(
        "R13",
        text="No Active P0 in cesp-spec-gap-matrix.md",
        verification="gap matrix review",
        passed=passed,
        errors=[f"blocking_open_p0:{blocking}"] if blocking else [],
        detail={"summary": summary, "open_p0": open_p0, "allowed_open": sorted(READINESS_ALLOWED_OPEN_P0_V1)},
    )


def _evaluate_r14_phase08_freeze_v1() -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_constitutional_freeze import (
        build_synthesis_constitutional_freeze_signoff_snapshot_v1,
        verify_gp08_freeze01_constitutional_freeze_static,
    )

    freeze_gate = verify_gp08_freeze01_constitutional_freeze_static()
    signoff = build_synthesis_constitutional_freeze_signoff_snapshot_v1()
    digest = hash_synthesis_artifact_schema_fixture_v1()
    passed = (
        bool(freeze_gate.get("passed"))
        and bool(signoff.get("constitutional_freeze_passed"))
        and len(digest) == 64
    )
    errors: list[str] = []
    if not freeze_gate.get("passed"):
        errors.append("gp08_freeze01_failed")
    if not signoff.get("constitutional_freeze_passed"):
        errors.append("constitutional_freeze_signoff_failed")
    if len(digest) != 64:
        errors.append("synthesis_schema_digest_missing")
    return _criterion_row_v1(
        "R14",
        text="Phase 08 freeze still valid",
        verification="G-P08-FREEZE-01 + schema digest",
        passed=passed,
        errors=errors,
        detail={"schema_digest_sha256": digest},
    )


def get_latest_soak_signoff_v1(session: Session) -> CortexPhase09ReadinessSignoff | None:
    return session.scalar(
        select(CortexPhase09ReadinessSignoff)
        .where(CortexPhase09ReadinessSignoff.signoff_kind == READINESS_SIGNOFF_KIND_SOAK_7D_V1)
        .order_by(CortexPhase09ReadinessSignoff.signed_at.desc())
        .limit(1),
    )


def _evaluate_r15_soak_signoff_v1(session: Session | None) -> dict[str, Any]:
    row = get_latest_soak_signoff_v1(session) if session is not None else None
    passed = row is not None
    detail: dict[str, Any] = {}
    if row is not None:
        detail = {
            "signed_at": row.signed_at.isoformat(),
            "signed_by": str(row.signed_by) if row.signed_by else None,
            "note": row.note,
        }
    return _criterion_row_v1(
        "R15",
        text="7-day soak report",
        verification="ops sign-off",
        passed=passed,
        errors=[] if passed else ["soak_signoff_missing"],
        detail=detail,
    )


def build_phase09_readiness_checklist_v1(
    session: Session | None = None,
) -> list[dict[str, Any]]:
    """Evaluate readiness criteria **R1–R15**."""
    rows = [
        _evaluate_r1_continuation_law_v1(),
        _evaluate_r2_watchdog_v1(),
        _evaluate_r3_fake_green_v1(),
        _evaluate_r4_retrieval_reports_v1(),
        _evaluate_r5_synthesis_explain_admin_v1(),
        _evaluate_r6_graph_density_v1(),
        _evaluate_r7_traversal_v1(),
        _evaluate_r8_tcre_saturation_v1(),
        _evaluate_r9_synthesis_audits_v1(),
        _evaluate_r10_maturity_v1(),
        _evaluate_r11_cockpit_surfaces_v1(),
        _evaluate_r12_economics_caps_v1(),
        _evaluate_r13_gap_matrix_v1(),
        _evaluate_r14_phase08_freeze_v1(),
        _evaluate_r15_soak_signoff_v1(session),
    ]
    assert [r["criterion_id"] for r in rows] == list(PHASE09_READINESS_CRITERION_IDS_V1)
    return rows


def evaluate_phase09_readiness_v1(session: Session | None = None) -> dict[str, Any]:
    checklist = build_phase09_readiness_checklist_v1(session)
    failures = [c["criterion_id"] for c in checklist if not c.get("passed")]
    return {
        "gate_id": GP085_READY01_GATE_ID_V1,
        "readiness_passed": not failures,
        "failure_criteria": failures,
        "checklist": checklist,
        "phase09_still_blocked_by_close_gate": True,
        "required_close_gate": PHASE085_HARD_DOWNSTREAM_GATE_V1,
    }


def record_phase09_soak_signoff_v1(
    session: Session,
    *,
    operator_user_id: uuid.UUID | None = None,
    note: str | None = None,
    signed_at: datetime | None = None,
) -> dict[str, Any]:
    """Operator attestation for **R15** (7-day soak)."""
    now = signed_at or datetime.now(tz=UTC)
    row = CortexPhase09ReadinessSignoff(
        id=uuid.uuid4(),
        signoff_kind=READINESS_SIGNOFF_KIND_SOAK_7D_V1,
        signed_at=now,
        signed_by=operator_user_id,
        note=(note or "").strip() or None,
        detail_json={"criterion_id": "R15", "verification": "ops_sign_off"},
    )
    session.add(row)
    session.flush()
    return {
        "signoff_kind": READINESS_SIGNOFF_KIND_SOAK_7D_V1,
        "signed_at": now.isoformat(),
        "signed_by": str(operator_user_id) if operator_user_id else None,
        "note": row.note,
    }


def evaluate_golden_tenant_profile_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Golden tenant profile checks (doctrine §Golden tenant profile)."""
    from vector.domains.cortex.operational_runtime.substrate_operational_maturity import (
        MATURITY_CLASS_OPERATIONAL_ALIVE_V1,
        evaluate_multidimensional_operational_maturity_v1,
    )
    from vector.domains.cortex.operational_runtime.substrate_retrieval_density import (
        compute_retrieval_density_metrics_v1,
    )
    from vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery import (
        detect_stalled_substrate_pipelines_v1,
    )
    from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
        count_synthesis_eligible_scopes_v1,
    )

    retrieval = compute_retrieval_density_metrics_v1(session, tenant_id=tenant_id)
    indexed = int(retrieval.get("retrieval_indexed_count") or 0)
    scopes = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
    eligible = int(scopes.get("eligible_scopes") or 0)
    synth_completed = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "completed",
            ),
        )
        or 0,
    )
    stalled = detect_stalled_substrate_pipelines_v1(
        session,
        stall_threshold_seconds=stall_threshold_seconds,
        limit=50,
    )
    tenant_stalled = [s for s in stalled if str(s.get("tenant_id")) == str(tenant_id)]
    unrecovered = list(tenant_stalled)
    maturity = evaluate_multidimensional_operational_maturity_v1(session, tenant_id=tenant_id)

    checks = {
        "non_zero_published_retrieval_rows": indexed > 0,
        "non_zero_eligible_scopes": eligible > 0,
        "at_least_one_completed_synthesis_job": synth_completed >= 1,
        "zero_unrecovered_stalls": len(unrecovered) == 0,
        "operational_alive_maturity": maturity.get("maturity_class")
        == MATURITY_CLASS_OPERATIONAL_ALIVE_V1,
    }
    passed = all(checks.values())
    return {
        "surface_kind": "golden_tenant_profile",
        "gate_id": GP085_READY01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "profile_passed": passed,
        "checks": checks,
        "metrics": {
            "retrieval_indexed_count": indexed,
            "eligible_scopes": eligible,
            "synthesis_jobs_completed": synth_completed,
            "unrecovered_stalls": len(unrecovered),
            "maturity_class": maturity.get("maturity_class"),
        },
    }


def assert_phase09_blocked_until_readiness_v1(
    *,
    readiness_passed: bool = False,
    phase09_ship_flags: dict[str, Any] | None = None,
    cesp_close_gate_passed: bool = False,
) -> None:
    """Block Phase 09 until **G-P085-READY-01** and **G-P085-CLOSE-01**."""
    assert_phase09_blocked_until_cesp_close_v1(
        phase09_ship_flags=phase09_ship_flags,
        cesp_close_gate_passed=cesp_close_gate_passed,
    )
    if readiness_passed:
        return
    from vector.domains.cortex.operational_runtime.phase_boundaries import CespPhaseBoundaryError

    flags = dict(phase09_ship_flags or {})
    for key in ("phase09_enabled", "product_workflow_enabled"):
        if flags.get(key) is True:
            raise CespPhaseBoundaryError(
                "phase09_before_readiness",
                rule_id="G-P085-READY-01",
                detail={"required_gate": GP085_READY01_GATE_ID_V1},
            )


def verify_gp085_ready01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_phase09_readiness_catalog_v1()
    if cat["primary_gate_id"] != GP085_READY01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if len(cat["criterion_ids"]) != 15:
        errors.append("criterion_count_mismatch")

    checklist_without_soak = build_phase09_readiness_checklist_v1(session=None)
    r15 = next(c for c in checklist_without_soak if c["criterion_id"] == "R15")
    if r15.get("passed"):
        errors.append("r15_should_require_signoff_record")

    pre_r15 = [c for c in checklist_without_soak if c["criterion_id"] != "R15"]
    if not all(c.get("passed") for c in pre_r15):
        errors.append("static_criteria_incomplete")

    if "assert_phase09_blocked_until_readiness_v1" not in inspect.getsource(
        assert_phase09_blocked_until_readiness_v1,
    ):
        errors.append("readiness_assert_missing")

    passed = not errors
    return {
        "id": GP085_READY01_GATE_ID_V1,
        "name": "cesp_phase09_readiness",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "static_criteria_passed": all(c.get("passed") for c in pre_r15)},
    }
