"""Phase 07 P07-29 — implementation sequencing (waves 0–5) + Phase 08 handoff.

Normative: ``DOCS/cortex/retrieval/phase-07-implementation-sequencing-plan.md``.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.retrieval.normative import (
    PHASE07_STEP_PROGRAM_COUNT,
    PHASE07_SUBSTRATE_PIPELINE_STAGES_V1,
)

PHASE07_RETRIEVAL_IMPLEMENTATION_SEQUENCING_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_IMPLEMENTATION_SEQUENCING_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-implementation-sequencing-plan.md"
)

RETRIEVAL_EVIDENCE_HIT_SCHEMA_LITERAL_V1: Final[str] = "RetrievalEvidenceHitV1"

GP07_SEQ01_GATE_ID_V1: Final[str] = "G-P07-SEQ-01"
GP07_SEQ02_GATE_ID_V1: Final[str] = "G-P07-SEQ-02"
GP07_SEQ03_GATE_ID_V1: Final[str] = "G-P07-SEQ-03"
GP07_SEQ04_GATE_ID_V1: Final[str] = "G-P07-SEQ-04"
GP07_SEQ05_GATE_ID_V1: Final[str] = "G-P07-SEQ-05"

RETRIEVAL_IMPLEMENTATION_WAVE_IDS_V1: Final[tuple[str, ...]] = (
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
)

RETRIEVAL_CRITICAL_PATH_MODULE_CHAIN_V1: Final[tuple[str, ...]] = (
    "vector.domains.cortex.retrieval.anti_goals",
    "vector.domains.cortex.retrieval.query_contract",
    "vector.domains.cortex.retrieval.retrieval_addressing",
    "vector.domains.cortex.retrieval.retrieval_tcre_binding",
    "vector.domains.cortex.retrieval.retrieval_query_engine",
    "vector.domains.cortex.retrieval.retrieval_replay_equivalence",
    "vector.domains.cortex.retrieval.retrieval_index_materialization",
    "vector.domains.cortex.retrieval.retrieval_completeness_projection",
    "vector.domains.cortex.retrieval.retrieval_control_plane",
    "vector.domains.cortex.retrieval.retrieval_certification_pack",
)

RETRIEVAL_TRACKER_STEP_WAVE_RANGES_V1: Final[tuple[tuple[int, int, str], ...]] = (
    (1, 9, "0-1"),
    (10, 13, "1-2"),
    (14, 18, "2-3"),
    (19, 21, "3"),
    (22, 26, "4"),
    (27, 30, "5"),
)

RETRIEVAL_PARALLEL_TRACKS_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "track_id": "frontend_admin",
        "can_parallelize_after": "Wave 2.3 (API stubs)",
    },
    {
        "track_id": "celery_index_jobs",
        "can_parallelize_after": "Wave 3.1",
    },
    {
        "track_id": "golden_vectors",
        "can_parallelize_after": "Wave 1.3",
    },
)

@dataclass(frozen=True, slots=True)
class _WaveDeliverableV1:
    deliverable_id: str
    label: str
    module: str | None = None
    symbols: tuple[str, ...] = ()
    gate_runner: str | None = None
    doc_marker: str | None = None


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        if (root / "DOCS" / "cortex" / "retrieval" / "phase-07-normative-index.md").is_file():
            return root
        alt = root / "backend"
        if (alt / "src" / "vector" / "domains" / "cortex" / "retrieval").is_dir() and (
            root / "DOCS" / "cortex" / "retrieval" / "phase-07-normative-index.md"
        ).is_file():
            return root
    msg = "repo root not found for phase 07 docs"
    raise FileNotFoundError(msg)


def _module_symbols_wired(module_path: str, symbols: Sequence[str]) -> list[str]:
    errors: list[str] = []
    try:
        mod = importlib.import_module(module_path)
    except ImportError as exc:
        return [f"import_failed:{module_path}:{exc}"]
    for sym in symbols:
        if not hasattr(mod, sym):
            errors.append(f"missing_symbol:{module_path}.{sym}")
    return errors


def _run_gate_runner(dotted: str) -> dict[str, Any]:
    mod_name, _, fn_name = dotted.rpartition(".")
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, fn_name)
    out = fn()
    if not isinstance(out, dict):
        return {"passed": False, "detail": {"errors": [f"gate_runner_bad_return:{dotted}"]}}
    return out


def _wave_deliverables_v1() -> dict[str, tuple[_WaveDeliverableV1, ...]]:
    return {
        "0": (
            _WaveDeliverableV1(
                "0.0",
                "Doctrine freeze tree",
                doc_marker="phase-07-normative-index.md",
            ),
            _WaveDeliverableV1(
                "0.1",
                "MASTER_TRACKER 30-step program",
                doc_marker="MASTER_TRACKER|Phase 07",
            ),
        ),
        "1": (
            _WaveDeliverableV1(
                "1.1",
                "normative + anti_goals",
                "vector.domains.cortex.retrieval.normative",
                ("PHASE07_PROGRAM_FREEZE_VERSION", "build_phase07_normative_program_document_v1"),
            ),
            _WaveDeliverableV1(
                "1.1b",
                "G-P07-ANTI gates",
                "vector.domains.cortex.retrieval.anti_goals",
                ("verify_gp07_anti01_retrieval_package_static",),
                gate_runner=(
                    "vector.domains.cortex.retrieval.anti_goals."
                    "verify_gp07_anti01_retrieval_package_static"
                ),
            ),
            _WaveDeliverableV1(
                "1.2",
                "query_contract + G-P07-SCHEMA-01",
                "vector.domains.cortex.retrieval.query_contract",
                ("build_retrieval_query_contract_catalog_v1",),
                gate_runner=(
                    "vector.domains.cortex.retrieval.anti_goals."
                    "verify_gp07_schema01_retrieval_query_envelope_forbidden_keys_static"
                ),
            ),
            _WaveDeliverableV1(
                "1.3",
                "addressing + golden vectors",
                "vector.domains.cortex.retrieval.retrieval_addressing",
                ("retrieval_golden_vectors_v1_root", "verify_gp07_addr01_golden_corpus_static"),
            ),
            _WaveDeliverableV1(
                "1.4",
                "legality + degradation registry",
                "vector.domains.cortex.retrieval.retrieval_legality_matrix",
                ("build_retrieval_legality_matrix_catalog_v1",),
            ),
            _WaveDeliverableV1(
                "1.4b",
                "RD-* taxonomy (RET-DEG-01)",
                "vector.domains.cortex.retrieval.retrieval_bounded_caps",
                ("verify_gp07_deg01_rd_registry_closed_static",),
            ),
        ),
        "2": (
            _WaveDeliverableV1(
                "2.1",
                "TCRE binding read path",
                "vector.domains.cortex.retrieval.retrieval_tcre_binding",
                ("build_retrieval_tcre_binding_catalog_v1",),
            ),
            _WaveDeliverableV1(
                "2.2",
                "OCTS durable walk binding",
                "vector.domains.cortex.retrieval.retrieval_octs_binding",
                ("build_retrieval_traversal_binding_catalog_v1",),
            ),
            _WaveDeliverableV1(
                "2.3",
                "query engine + execution FSM",
                "vector.domains.cortex.retrieval.query_execution",
                ("execute_retrieval_query_envelope_v1",),
            ),
            _WaveDeliverableV1(
                "2.4a",
                "provenance envelope",
                "vector.domains.cortex.retrieval.retrieval_provenance_evidence",
                ("build_retrieval_evidence_hit_v1",),
            ),
            _WaveDeliverableV1(
                "2.4b",
                "deterministic ranking",
                "vector.domains.cortex.retrieval.retrieval_ranking_selection",
                ("verify_gp07_rank01_no_float_scores_static",),
            ),
            _WaveDeliverableV1(
                "2.5",
                "G-P07-REPLAY-01 harness (wave 2.5 gate)",
                gate_runner=(
                    "vector.domains.cortex.retrieval.retrieval_replay_equivalence."
                    "verify_gp07_replay_01_canonical_identity_stable_static"
                ),
            ),
        ),
        "3": (
            _WaveDeliverableV1(
                "3.1",
                "index materialization substrate",
                "vector.domains.cortex.retrieval.retrieval_index_materialization",
                ("build_retrieval_index_catalog_v1", "run_retrieval_index_rebuild_v1"),
            ),
            _WaveDeliverableV1(
                "3.3",
                "completeness projection",
                "vector.domains.cortex.retrieval.retrieval_completeness_projection",
                ("project_retrieval_completeness_v1", "verify_gp07_comp01_never_idle_healthy_static"),
            ),
            _WaveDeliverableV1(
                "3.4",
                "degradation propagation table",
                "vector.domains.cortex.retrieval.retrieval_degradation_taxonomy",
                ("verify_gp07_deg03_propagation_table_static",),
            ),
        ),
        "4": (
            _WaveDeliverableV1(
                "4.1",
                "control plane + readiness economics",
                "vector.domains.cortex.retrieval.retrieval_control_plane",
                ("verify_gp07_cp01_retrieval_control_plane_rbac_static",),
            ),
            _WaveDeliverableV1(
                "4.1b",
                "readiness economics receipt",
                "vector.domains.cortex.retrieval.retrieval_readiness_economics",
                ("build_retrieval_readiness_economics_receipt_v1",),
            ),
            _WaveDeliverableV1(
                "4.2",
                "operator workflows + SPA registry",
                "vector.domains.cortex.retrieval.retrieval_operator_workflows",
                ("build_retrieval_operator_workflows_catalog_v1",),
            ),
            _WaveDeliverableV1(
                "4.3",
                "query audit trail",
                "vector.domains.cortex.retrieval.retrieval_control_plane",
                ("list_retrieval_query_audit_trail_v1",),
            ),
            _WaveDeliverableV1(
                "4.4",
                "tenant verification slice",
                "vector.domains.cortex.retrieval.retrieval_tenant_verification_slice",
                ("build_org_graph_retrieval_verification_slice_v1",),
            ),
        ),
        "5": (
            _WaveDeliverableV1(
                "5.1",
                "RETRIEVAL-CERT-PACK-1 + G-P07-CLOSE-01",
                "vector.domains.cortex.retrieval.retrieval_certification_pack",
                ("verify_retrieval_cert_pack_v1", "verify_gp07_close01_retrieval_cert_pack_closure_static"),
            ),
            _WaveDeliverableV1(
                "5.2",
                "runtime legality matrix enforcement",
                "vector.domains.cortex.retrieval.retrieval_runtime_legality_matrix",
                ("verify_gp07_rlm01_retrieval_runtime_legality_matrix_static_bundle",),
            ),
        ),
    }


def evaluate_retrieval_wave_deliverable_v1(deliverable: _WaveDeliverableV1) -> dict[str, Any]:
    """Return per-deliverable wiring status (module symbols + optional gate runner)."""
    errors: list[str] = []
    gate_passed: bool | None = None
    if deliverable.doc_marker:
        root = _repo_root()
        if deliverable.doc_marker.startswith("MASTER_TRACKER"):
            path = root / "DOCS" / "cortex" / "MASTER_TRACKER.md"
            if not path.is_file():
                errors.append("missing_master_tracker")
            else:
                text = path.read_text(encoding="utf-8")
                if "Phase 07" not in text or "Retrieval & Query Engine" not in text:
                    errors.append("master_tracker_missing_phase07_section")
        else:
            doc_path = root / "DOCS" / "cortex" / "retrieval" / deliverable.doc_marker
            if not doc_path.is_file():
                errors.append(f"missing_doc:{deliverable.doc_marker}")
    if deliverable.module:
        errors.extend(_module_symbols_wired(deliverable.module, deliverable.symbols))
    if deliverable.gate_runner:
        gate_out = _run_gate_runner(deliverable.gate_runner)
        gate_passed = gate_out.get("passed") is True
        if not gate_passed:
            errors.append(f"gate_failed:{deliverable.gate_runner}")
    passed = len(errors) == 0
    return {
        "deliverable_id": deliverable.deliverable_id,
        "label": deliverable.label,
        "passed": passed,
        "errors": errors,
        "gate_passed": gate_passed,
    }


def evaluate_retrieval_implementation_wave_v1(wave_id: str) -> dict[str, Any]:
    """Evaluate one sequencing wave (**0** … **5**)."""
    waves = _wave_deliverables_v1()
    if wave_id not in waves:
        return {
            "wave_id": wave_id,
            "passed": False,
            "errors": [f"unknown_wave:{wave_id}"],
            "deliverables": [],
        }
    rows = [evaluate_retrieval_wave_deliverable_v1(d) for d in waves[wave_id]]
    passed = all(bool(r.get("passed")) for r in rows)
    return {
        "wave_id": wave_id,
        "passed": passed,
        "deliverable_count": len(rows),
        "deliverables": rows,
    }


def evaluate_all_retrieval_implementation_waves_v1() -> dict[str, Any]:
    """Evaluate waves **0** through **5** (runtime handoff snapshot)."""
    wave_rows = [evaluate_retrieval_implementation_wave_v1(wid) for wid in RETRIEVAL_IMPLEMENTATION_WAVE_IDS_V1]
    return {
        "passed": all(bool(w.get("passed")) for w in wave_rows),
        "waves": wave_rows,
    }


def build_retrieval_tracker_step_wave_map_v1() -> list[dict[str, Any]]:
    """Tracker steps **1–30** → sequencing wave label (doctrine table)."""
    rows: list[dict[str, Any]] = []
    for lo, hi, wave_label in RETRIEVAL_TRACKER_STEP_WAVE_RANGES_V1:
        for step in range(lo, hi + 1):
            rows.append({"tracker_step": step, "wave_label": wave_label})
    return rows


def build_retrieval_phase08_readiness_checklist_v1() -> list[dict[str, Any]]:
    """Phase 08 pre-coding checklist with static wiring status."""
    items: list[dict[str, Any]] = []

    hit_errors = _module_symbols_wired(
        "vector.domains.cortex.retrieval.retrieval_provenance_evidence",
        ("build_retrieval_evidence_hit_v1",),
    )
    items.append(
        {
            "checklist_id": "P08-CHK-01",
            "text": f"{RETRIEVAL_EVIDENCE_HIT_SCHEMA_LITERAL_V1} schema frozen",
            "passed": len(hit_errors) == 0,
            "errors": hit_errors,
        }
    )

    from vector.domains.cortex.retrieval.phase_boundaries import (
        verify_gp07_bnd08_synthesis_boundary_static,
    )

    bnd08 = verify_gp07_bnd08_synthesis_boundary_static()
    items.append(
        {
            "checklist_id": "P08-CHK-02",
            "text": "Phase 08 ingress rejects non-authoritative retrieval (RET-BND-08)",
            "passed": bnd08.get("passed") is True,
            "errors": [] if bnd08.get("passed") else ["bnd08_gate_failed"],
        }
    )

    from vector.domains.cortex.retrieval.retrieval_addressing import retrieval_golden_vectors_v1_root

    query_case_errors: list[str] = []
    root = retrieval_golden_vectors_v1_root()
    query_cases = sorted(root.glob("cases/query/*/case.json"))
    if not query_cases:
        query_case_errors.append("missing_golden_query_cases")
    items.append(
        {
            "checklist_id": "P08-CHK-03",
            "text": "Sample queries documented for synthesis fixtures",
            "passed": len(query_case_errors) == 0,
            "errors": query_case_errors,
            "query_case_count": len(query_cases),
        }
    )
    return items


def build_retrieval_implementation_sequencing_catalog_v1() -> dict[str, Any]:
    """Operator/CI catalog: waves, critical path, tracker map, Phase 08 handoff."""
    waves_eval = evaluate_all_retrieval_implementation_waves_v1()
    p08 = build_retrieval_phase08_readiness_checklist_v1()
    return {
        "phase07_retrieval_implementation_sequencing_runtime_schema_version": (
            PHASE07_RETRIEVAL_IMPLEMENTATION_SEQUENCING_RUNTIME_SCHEMA_VERSION
        ),
        "spec_ref": RETRIEVAL_IMPLEMENTATION_SEQUENCING_SPEC_REF_V1,
        "wave_ids": list(RETRIEVAL_IMPLEMENTATION_WAVE_IDS_V1),
        "critical_path_modules": list(RETRIEVAL_CRITICAL_PATH_MODULE_CHAIN_V1),
        "substrate_pipeline_stages": list(PHASE07_SUBSTRATE_PIPELINE_STAGES_V1),
        "tracker_step_program_count": int(PHASE07_STEP_PROGRAM_COUNT),
        "tracker_step_wave_map": build_retrieval_tracker_step_wave_map_v1(),
        "parallel_tracks": [dict(t) for t in RETRIEVAL_PARALLEL_TRACKS_V1],
        "wave_evaluation": waves_eval,
        "phase08_readiness_checklist": p08,
        "phase08_readiness_passed": all(bool(i.get("passed")) for i in p08),
        "all_waves_passed": waves_eval.get("passed"),
    }


def _seq_meta(gate_id: str, name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_seq01_implementation_sequencing_catalog_static() -> dict[str, Any]:
    """**G-P07-SEQ-01** — sequencing catalog shape + six waves."""
    errors: list[str] = []
    cat = build_retrieval_implementation_sequencing_catalog_v1()
    if cat.get("phase07_retrieval_implementation_sequencing_runtime_schema_version", 0) < 1:
        errors.append("runtime_schema_version")
    if tuple(cat.get("wave_ids") or []) != RETRIEVAL_IMPLEMENTATION_WAVE_IDS_V1:
        errors.append("wave_ids_drift")
    if len(cat.get("tracker_step_wave_map") or []) != PHASE07_STEP_PROGRAM_COUNT:
        errors.append("tracker_map_count")
    if len(cat.get("critical_path_modules") or []) != len(RETRIEVAL_CRITICAL_PATH_MODULE_CHAIN_V1):
        errors.append("critical_path_length")
    return _seq_meta(GP07_SEQ01_GATE_ID_V1, "retrieval_implementation_sequencing_catalog", errors)


def verify_gp07_seq02_tracker_wave_mapping_static() -> dict[str, Any]:
    """**G-P07-SEQ-02** — tracker step ranges match doctrine table."""
    errors: list[str] = []
    rows = build_retrieval_tracker_step_wave_map_v1()
    steps = {int(r["tracker_step"]) for r in rows}
    want = set(range(1, PHASE07_STEP_PROGRAM_COUNT + 1))
    if steps != want:
        errors.append(f"step_coverage_got_{sorted(steps)}")
    for lo, hi, label in RETRIEVAL_TRACKER_STEP_WAVE_RANGES_V1:
        for step in range(lo, hi + 1):
            row = next((r for r in rows if int(r["tracker_step"]) == step), None)
            if row is None or row.get("wave_label") != label:
                errors.append(f"step_{step}_wave_label_mismatch")
    return _seq_meta(GP07_SEQ02_GATE_ID_V1, "retrieval_tracker_wave_mapping", errors)


def verify_gp07_seq03_critical_path_modules_static() -> dict[str, Any]:
    """**G-P07-SEQ-03** — critical path modules importable in order."""
    errors: list[str] = []
    for mod_path in RETRIEVAL_CRITICAL_PATH_MODULE_CHAIN_V1:
        errors.extend(_module_symbols_wired(mod_path, ()))
    return _seq_meta(GP07_SEQ03_GATE_ID_V1, "retrieval_critical_path_modules", errors)


def verify_gp07_seq04_waves_zero_through_five_complete_static() -> dict[str, Any]:
    """**G-P07-SEQ-04** — runtime handoff: waves **0–5** deliverables wired."""
    errors: list[str] = []
    body = evaluate_all_retrieval_implementation_waves_v1()
    if not body.get("passed"):
        for wave in body.get("waves") or []:
            if not wave.get("passed"):
                wid = wave.get("wave_id")
                for d in wave.get("deliverables") or []:
                    if not d.get("passed"):
                        errors.append(
                            f"wave_{wid}:{d.get('deliverable_id')}:"
                            f"{d.get('errors')}"
                        )
    return _seq_meta(GP07_SEQ04_GATE_ID_V1, "retrieval_waves_0_5_complete", errors)


def verify_gp07_seq05_phase08_readiness_handoff_static() -> dict[str, Any]:
    """**G-P07-SEQ-05** — Phase 08 readiness checklist (static items green)."""
    errors: list[str] = []
    for item in build_retrieval_phase08_readiness_checklist_v1():
        if not item.get("passed"):
            errors.append(f"{item.get('checklist_id')}:{item.get('errors')}")
    return _seq_meta(GP07_SEQ05_GATE_ID_V1, "retrieval_phase08_readiness_handoff", errors)
