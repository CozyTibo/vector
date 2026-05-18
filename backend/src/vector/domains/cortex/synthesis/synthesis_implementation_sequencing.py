"""Phase 08 P08-29 — implementation sequencing (waves 0–7) + Phase 09 handoff.

Normative: ``DOCS/cortex/synthesis/phase-08-implementation-sequencing-plan.md``.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.synthesis.normative import (
    PHASE08_STEP_PROGRAM_COUNT,
    PHASE08_SUBSTRATE_PIPELINE_STAGES_V1,
)

PHASE08_SYNTHESIS_IMPLEMENTATION_SEQUENCING_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_IMPLEMENTATION_SEQUENCING_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-implementation-sequencing-plan.md"
)

SYNTHESIS_INTELLIGENCE_ARTIFACT_SCHEMA_LITERAL_V1: Final[str] = "SynthesisIntelligenceArtifactV1"

GP08_SEQ01_GATE_ID_V1: Final[str] = "G-P08-SEQ-01"
GP08_SEQ02_GATE_ID_V1: Final[str] = "G-P08-SEQ-02"
GP08_SEQ03_GATE_ID_V1: Final[str] = "G-P08-SEQ-03"
GP08_SEQ04_GATE_ID_V1: Final[str] = "G-P08-SEQ-04"
GP08_SEQ05_GATE_ID_V1: Final[str] = "G-P08-SEQ-05"
GP08_SEQ06_GATE_ID_V1: Final[str] = "G-P08-SEQ-06"

SYNTHESIS_IMPLEMENTATION_WAVE_IDS_V1: Final[tuple[str, ...]] = (
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
)

SYNTHESIS_IMPLEMENTATION_WAVES_ZERO_THROUGH_FIVE_V1: Final[tuple[str, ...]] = (
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
)

SYNTHESIS_CRITICAL_PATH_MODULE_CHAIN_V1: Final[tuple[str, ...]] = (
    "vector.domains.cortex.synthesis.anti_goals",
    "vector.domains.cortex.synthesis.synthesis_job_contract",
    "vector.domains.cortex.synthesis.synthesis_ingress",
    "vector.domains.cortex.synthesis.synthesis_query_plan",
    "vector.domains.cortex.synthesis.synthesis_orchestrator",
    "vector.domains.cortex.synthesis.synthesis_llm_router",
    "vector.domains.cortex.synthesis.synthesis_artifact_materialization",
    "vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs",
    "vector.domains.cortex.synthesis.synthesis_control_plane",
    "vector.domains.cortex.synthesis.synthesis_verification_harness",
)

SYNTHESIS_TRACKER_STEP_WAVE_RANGES_V1: Final[tuple[tuple[int, int, str], ...]] = (
    (1, 3, "0"),
    (4, 9, "1"),
    (10, 14, "2"),
    (15, 18, "3"),
    (19, 23, "4"),
    (24, 28, "5"),
    (29, 30, "6"),
    (31, 35, "7"),
)

SYNTHESIS_PARALLEL_TRACKS_V1: Final[tuple[dict[str, str], ...]] = (
    {"track_id": "frontend_admin", "can_parallelize_after": "Step 22"},
    {"track_id": "golden_vectors", "can_parallelize_after": "Step 17"},
    {"track_id": "pipeline", "can_parallelize_after": "Step 14 (stub), Step 31 (full)"},
    {"track_id": "llm_vendor_real_adapter", "can_parallelize_after": "Step 11 (behind flag)"},
)

SYNTHESIS_IMPLEMENTATION_SEQUENCING_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/catalog/cortex/synthesis/implementation-sequencing",
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
        if (root / "DOCS" / "cortex" / "synthesis" / "phase-08-normative-index.md").is_file():
            return root
    msg = "repo root not found for phase 08 docs"
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
                doc_marker="phase-08-normative-index.md",
            ),
            _WaveDeliverableV1(
                "0.1",
                "MASTER_TRACKER Phase 08 program",
                doc_marker="MASTER_TRACKER|Phase 08",
            ),
            _WaveDeliverableV1(
                "0.2",
                "Normative program freeze",
                "vector.domains.cortex.synthesis.normative",
                ("PHASE08_PROGRAM_FREEZE_VERSION", "build_phase08_normative_program_document_v1"),
            ),
            _WaveDeliverableV1(
                "0.3",
                "G-P08-ANTI-01 package scan",
                gate_runner=(
                    "vector.domains.cortex.synthesis.anti_goals."
                    "verify_gp08_anti01_synthesis_package_static"
                ),
            ),
            _WaveDeliverableV1(
                "0.4",
                "SYN-BND catalog",
                gate_runner=(
                    "vector.domains.cortex.synthesis.phase_boundaries."
                    "verify_gp08_bnd_catalog_static"
                ),
            ),
        ),
        "1": (
            _WaveDeliverableV1(
                "1.1",
                "Retrieval ingress law",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_ingress."
                    "verify_gp08_ingress01_retrieval_evidence_ingress_static"
                ),
            ),
            _WaveDeliverableV1(
                "1.2",
                "Job contract + workload/intent",
                "vector.domains.cortex.synthesis.synthesis_job_contract",
                ("build_synthesis_job_contract_catalog_v1",),
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_job_contract."
                    "verify_gp08_schema01_synthesis_workload_intent_registry_static"
                ),
            ),
            _WaveDeliverableV1(
                "1.3",
                "Job envelope + replay identity",
                "vector.domains.cortex.synthesis.synthesis_job_envelope",
                ("compute_synthesis_job_envelope_digest_v1",),
            ),
            _WaveDeliverableV1(
                "1.4",
                "S-LEG legality matrix",
                "vector.domains.cortex.synthesis.synthesis_legality_matrix",
                ("build_synthesis_legality_matrix_catalog_v1",),
            ),
            _WaveDeliverableV1(
                "1.5",
                "SYN-REP-01 replay identity",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_replay_equivalence."
                    "verify_gp08_replay01_canonical_identity_stable_static"
                ),
            ),
            _WaveDeliverableV1(
                "1.6",
                "G-P08-CITE-01 cite-or-omit",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_evidence_binding."
                    "verify_gp08_cite01_cite_or_omit_static"
                ),
            ),
        ),
        "2": (
            _WaveDeliverableV1(
                "2.1",
                "Retrieval plan + RETRIEVE path",
                "vector.domains.cortex.synthesis.synthesis_query_plan",
                ("execute_synthesis_retrieval_plan_v1",),
            ),
            _WaveDeliverableV1(
                "2.2",
                "Orchestrator shell",
                "vector.domains.cortex.synthesis.synthesis_orchestrator",
                ("execute_synthesis_job_envelope_v1",),
            ),
            _WaveDeliverableV1(
                "2.3",
                "LLM adapter isolation",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_llm_router."
                    "verify_gp08_llm01_fake_adapter_determinism_static"
                ),
            ),
            _WaveDeliverableV1(
                "2.4",
                "Prompt assembly law",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_prompt_assembly."
                    "verify_gp08_prm01_prompt_hash_stable_static"
                ),
            ),
            _WaveDeliverableV1(
                "2.5",
                "SD registry + caps",
                "vector.domains.cortex.synthesis.synthesis_bounded_caps",
                ("validate_sd_code_registered_v1",),
            ),
            _WaveDeliverableV1(
                "2.6",
                "Artifact materialization",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_artifact_materialization."
                    "verify_gp08_schema01_synthesis_intelligence_artifact_static"
                ),
            ),
            _WaveDeliverableV1(
                "2.7",
                "Wave 2.5 replay gate (G-P08-REPLAY-01)",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs."
                    "verify_gp08_replay17_structural_twin_law_static"
                ),
            ),
        ),
        "3": (
            _WaveDeliverableV1(
                "3.1",
                "Retrieval/TCRE bindings copy",
                "vector.domains.cortex.synthesis.synthesis_bindings",
                ("build_synthesis_bindings_catalog_v1",),
            ),
            _WaveDeliverableV1(
                "3.2",
                "Artifact lineage",
                "vector.domains.cortex.synthesis.synthesis_lineage",
                ("build_synthesis_lineage_catalog_v1",),
            ),
            _WaveDeliverableV1(
                "3.3",
                "Replay equivalence proofs",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs."
                    "verify_gp08_replay17_golden_double_run_corpus_static"
                ),
            ),
            _WaveDeliverableV1(
                "3.4",
                "RD→SD degradation topology",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_degradation."
                    "verify_gp08_deg02_rd_to_sd_matrix_static"
                ),
            ),
        ),
        "4": (
            _WaveDeliverableV1(
                "4.1",
                "Substrate completeness projection",
                "vector.domains.cortex.synthesis.synthesis_completeness_projection",
                ("verify_gp08_comp01_never_idle_healthy_static",),
            ),
            _WaveDeliverableV1(
                "4.2",
                "Observability + health",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_observability."
                    "verify_gp08_obs01_metrics_and_health_static"
                ),
            ),
            _WaveDeliverableV1(
                "4.3",
                "Control plane catalog",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_control_plane."
                    "verify_gp08_cp01_synthesis_control_plane_rbac_static"
                ),
            ),
            _WaveDeliverableV1(
                "4.4",
                "Operator workflows + SPA registry",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_operator_workflows."
                    "verify_gp08_wf01_synthesis_spa_routes_complete_static"
                ),
            ),
            _WaveDeliverableV1(
                "4.5",
                "Artifact query substrate",
                "vector.domains.cortex.synthesis.synthesis_artifact_query",
                ("list_synthesis_artifacts_query_v1",),
            ),
        ),
        "5": (
            _WaveDeliverableV1(
                "5.1",
                "Tenant verification slice",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_tenant_verification."
                    "verify_gp08_tver01_org_graph_synthesis_slice_golden_static"
                ),
            ),
            _WaveDeliverableV1(
                "5.2",
                "Runtime legality matrix + PROD-SYN-01",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_runtime_legality_matrix."
                    "verify_gp08_rlm01_synthesis_runtime_legality_matrix_static_bundle"
                ),
            ),
            _WaveDeliverableV1(
                "5.3",
                "G-P08-* verification harness",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_verification_harness."
                    "verify_gp08_rvh01_synthesis_verification_harness_static_bundle"
                ),
            ),
            _WaveDeliverableV1(
                "5.4",
                "Golden vectors + policy fixture",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_golden_vectors."
                    "verify_gp08_gtc01_synthesis_golden_vectors_static_bundle"
                ),
            ),
            _WaveDeliverableV1(
                "5.5",
                "Evaluation harness G-P08-EVAL-*",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_evaluation."
                    "verify_gp08_eval01_synthesis_evaluation_static_bundle"
                ),
            ),
        ),
        "6": (
            _WaveDeliverableV1(
                "6.0",
                "Implementation sequencing meta (this module)",
                "vector.domains.cortex.synthesis.synthesis_implementation_sequencing",
                ("build_synthesis_implementation_sequencing_catalog_v1",),
            ),
            _WaveDeliverableV1(
                "6.1",
                "SYNTHESIS-CERT-PACK-1 shape (G-P08-CLOSE-01 prep)",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_certification_pack."
                    "verify_gp08_close01_synthesis_cert_pack_shape_reference_static"
                ),
            ),
        ),
        "7": (
            _WaveDeliverableV1(
                "7.0",
                "Substrate pipeline phase 08 spec",
                doc_marker="phase-08-pipeline-orchestration.md",
            ),
            _WaveDeliverableV1(
                "7.1",
                "PHASE_08_SYNTHESIS substrate stage wired",
                module="vector.domains.cortex.substrate_pipeline.constants",
                symbols=("PHASE_08_SYNTHESIS",),
            ),
            _WaveDeliverableV1(
                "7.2",
                "Substrate pipeline phase_08_synthesis runner",
                module="vector.domains.cortex.synthesis.synthesis_pipeline",
                symbols=("run_substrate_phase_08_synthesis_v1",),
            ),
            _WaveDeliverableV1(
                "7.3",
                "Synthesis publication barrier (G-P08-REPLAY-02)",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_replay_equivalence."
                    "verify_gp08_replay02_publication_epoch_forward_only_static"
                ),
            ),
            _WaveDeliverableV1(
                "7.4",
                "Durable store + idempotency (G-P08-STORE-01)",
                gate_runner=(
                    "vector.domains.cortex.synthesis.synthesis_repository."
                    "verify_gp08_store01_synthesis_durable_store_static"
                ),
            ),
            _WaveDeliverableV1(
                "7.5",
                "E2E operational certification (G-P08-E2E-01)",
                gate_runner=(
                    "vector.domains.cortex.synthesis.testing.e2e_operational_certification."
                    "verify_gp08_e2e01_operational_certification_static"
                ),
            ),
            _WaveDeliverableV1(
                "7.6",
                "Constitutional freeze sign-off module (Step 35)",
                module="vector.domains.cortex.synthesis.synthesis_constitutional_freeze",
                symbols=(
                    "build_synthesis_constitutional_freeze_catalog_v1",
                    "P08_FINAL_FREEZE_BUNDLE_ID_V1",
                ),
            ),
        ),
    }


def evaluate_synthesis_wave_deliverable_v1(deliverable: _WaveDeliverableV1) -> dict[str, Any]:
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
                if "Phase 08" not in text or "Synthesis & Intelligence" not in text:
                    errors.append("master_tracker_missing_phase08_section")
        else:
            doc_path = root / "DOCS" / "cortex" / "synthesis" / deliverable.doc_marker
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


def evaluate_synthesis_implementation_wave_v1(wave_id: str) -> dict[str, Any]:
    """Evaluate one sequencing wave (**0** … **7**)."""
    waves = _wave_deliverables_v1()
    if wave_id not in waves:
        return {
            "wave_id": wave_id,
            "passed": False,
            "errors": [f"unknown_wave:{wave_id}"],
            "deliverables": [],
        }
    rows = [evaluate_synthesis_wave_deliverable_v1(d) for d in waves[wave_id]]
    passed = all(bool(r.get("passed")) for r in rows)
    return {
        "wave_id": wave_id,
        "passed": passed,
        "deliverable_count": len(rows),
        "deliverables": rows,
    }


def evaluate_synthesis_implementation_waves_v1(
    wave_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Evaluate selected waves (default **0** … **5** runtime handoff)."""
    ids = tuple(wave_ids or SYNTHESIS_IMPLEMENTATION_WAVES_ZERO_THROUGH_FIVE_V1)
    wave_rows = [evaluate_synthesis_implementation_wave_v1(wid) for wid in ids]
    return {
        "passed": all(bool(w.get("passed")) for w in wave_rows),
        "wave_ids_evaluated": list(ids),
        "waves": wave_rows,
    }


def evaluate_all_synthesis_implementation_waves_v1() -> dict[str, Any]:
    """Evaluate waves **0** through **7** (full program snapshot)."""
    return evaluate_synthesis_implementation_waves_v1(SYNTHESIS_IMPLEMENTATION_WAVE_IDS_V1)


def build_synthesis_tracker_step_wave_map_v1() -> list[dict[str, Any]]:
    """Tracker steps **1–35** → sequencing wave label (doctrine table)."""
    rows: list[dict[str, Any]] = []
    for lo, hi, wave_label in SYNTHESIS_TRACKER_STEP_WAVE_RANGES_V1:
        for step in range(lo, hi + 1):
            rows.append({"tracker_step": step, "wave_label": wave_label})
    return rows


def build_synthesis_phase09_readiness_checklist_v1() -> list[dict[str, Any]]:
    """Phase 09 pre-coding checklist with static wiring status (post Step 28)."""
    items: list[dict[str, Any]] = []

    artifact_errors = _module_symbols_wired(
        "vector.domains.cortex.synthesis.synthesis_artifact_query",
        ("list_synthesis_artifacts_query_v1",),
    )
    items.append(
        {
            "checklist_id": "P09-CHK-01",
            "text": (
                f"{SYNTHESIS_INTELLIGENCE_ARTIFACT_SCHEMA_LITERAL_V1} queryable by "
                "artifact_id + synthesis_publication_epoch"
            ),
            "passed": len(artifact_errors) == 0,
            "errors": artifact_errors,
        },
    )

    from vector.domains.cortex.synthesis.phase_boundaries import (
        verify_gp08_bnd09_products_boundary_static,
    )

    bnd09 = verify_gp08_bnd09_products_boundary_static()
    items.append(
        {
            "checklist_id": "P09-CHK-02",
            "text": "Phase 09 boundary tests green (SYN-BND-09)",
            "passed": bnd09.get("passed") is True,
            "errors": [] if bnd09.get("passed") else ["bnd09_gate_failed"],
        },
    )

    from vector.domains.cortex.synthesis.synthesis_certification_pack import (
        verify_gp08_close01_synthesis_cert_pack_shape_reference_static,
    )

    close_shape = verify_gp08_close01_synthesis_cert_pack_shape_reference_static()
    items.append(
        {
            "checklist_id": "P09-CHK-03",
            "text": "SYNTHESIS-CERT-PACK-1 shape + policy fixture pinned (Step 30 prep)",
            "passed": close_shape.get("passed") is True,
            "errors": [] if close_shape.get("passed") else ["close01_shape_failed"],
        },
    )

    golden_errors: list[str] = []
    from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
        synthesis_golden_corpus_case_count_v1,
    )

    if synthesis_golden_corpus_case_count_v1() < 4:
        golden_errors.append("golden_corpus_case_count_low")
    items.append(
        {
            "checklist_id": "P09-CHK-04",
            "text": "Golden corpus bound for synthesis replay/degradation fixtures",
            "passed": len(golden_errors) == 0,
            "errors": golden_errors,
            "golden_corpus_case_count": synthesis_golden_corpus_case_count_v1(),
        },
    )
    return items


def build_synthesis_implementation_sequencing_catalog_v1() -> dict[str, Any]:
    """Operator/CI catalog: waves, critical path, tracker map, Phase 09 handoff."""
    waves_0_5 = evaluate_synthesis_implementation_waves_v1()
    waves_all = evaluate_all_synthesis_implementation_waves_v1()
    p09 = build_synthesis_phase09_readiness_checklist_v1()
    return {
        "surface_kind": "doctrine_catalog",
        "phase08_synthesis_implementation_sequencing_runtime_schema_version": (
            PHASE08_SYNTHESIS_IMPLEMENTATION_SEQUENCING_RUNTIME_SCHEMA_VERSION
        ),
        "spec_ref": SYNTHESIS_IMPLEMENTATION_SEQUENCING_SPEC_REF_V1,
        "wave_ids": list(SYNTHESIS_IMPLEMENTATION_WAVE_IDS_V1),
        "waves_zero_through_five": list(SYNTHESIS_IMPLEMENTATION_WAVES_ZERO_THROUGH_FIVE_V1),
        "critical_path_modules": list(SYNTHESIS_CRITICAL_PATH_MODULE_CHAIN_V1),
        "substrate_pipeline_stages": list(PHASE08_SUBSTRATE_PIPELINE_STAGES_V1),
        "tracker_step_program_count": int(PHASE08_STEP_PROGRAM_COUNT),
        "tracker_step_wave_map": build_synthesis_tracker_step_wave_map_v1(),
        "parallel_tracks": [dict(t) for t in SYNTHESIS_PARALLEL_TRACKS_V1],
        "wave_evaluation_0_5": waves_0_5,
        "wave_evaluation_all": waves_all,
        "phase09_readiness_checklist": p09,
        "phase09_readiness_passed": all(bool(i.get("passed")) for i in p09),
        "all_waves_0_5_passed": waves_0_5.get("passed"),
        "all_waves_passed": waves_all.get("passed"),
    }


def _seq_meta(gate_id: str, name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_seq01_implementation_sequencing_catalog_static() -> dict[str, Any]:
    """**G-P08-SEQ-01** — sequencing catalog shape + eight waves."""
    errors: list[str] = []
    cat = build_synthesis_implementation_sequencing_catalog_v1()
    if cat.get("phase08_synthesis_implementation_sequencing_runtime_schema_version", 0) < 1:
        errors.append("runtime_schema_version")
    if tuple(cat.get("wave_ids") or []) != SYNTHESIS_IMPLEMENTATION_WAVE_IDS_V1:
        errors.append("wave_ids_drift")
    if len(cat.get("tracker_step_wave_map") or []) != PHASE08_STEP_PROGRAM_COUNT:
        errors.append("tracker_map_count")
    if len(cat.get("critical_path_modules") or []) != len(SYNTHESIS_CRITICAL_PATH_MODULE_CHAIN_V1):
        errors.append("critical_path_length")
    return _seq_meta(GP08_SEQ01_GATE_ID_V1, "synthesis_implementation_sequencing_catalog", errors)


def verify_gp08_seq02_tracker_wave_mapping_static() -> dict[str, Any]:
    """**G-P08-SEQ-02** — tracker step ranges match doctrine table."""
    errors: list[str] = []
    rows = build_synthesis_tracker_step_wave_map_v1()
    steps = {int(r["tracker_step"]) for r in rows}
    want = set(range(1, PHASE08_STEP_PROGRAM_COUNT + 1))
    if steps != want:
        errors.append(f"step_coverage_got_{sorted(steps)}")
    for lo, hi, label in SYNTHESIS_TRACKER_STEP_WAVE_RANGES_V1:
        for step in range(lo, hi + 1):
            row = next((r for r in rows if int(r["tracker_step"]) == step), None)
            if row is None or row.get("wave_label") != label:
                errors.append(f"step_{step}_wave_label_mismatch")
    return _seq_meta(GP08_SEQ02_GATE_ID_V1, "synthesis_tracker_wave_mapping", errors)


def verify_gp08_seq03_critical_path_modules_static() -> dict[str, Any]:
    """**G-P08-SEQ-03** — critical path modules importable in order."""
    errors: list[str] = []
    for mod_path in SYNTHESIS_CRITICAL_PATH_MODULE_CHAIN_V1:
        errors.extend(_module_symbols_wired(mod_path, ()))
    return _seq_meta(GP08_SEQ03_GATE_ID_V1, "synthesis_critical_path_modules", errors)


def verify_gp08_seq04_waves_zero_through_five_complete_static() -> dict[str, Any]:
    """**G-P08-SEQ-04** — runtime handoff: waves **0–5** deliverables wired."""
    errors: list[str] = []
    body = evaluate_synthesis_implementation_waves_v1()
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
    return _seq_meta(GP08_SEQ04_GATE_ID_V1, "synthesis_waves_0_5_complete", errors)


def verify_gp08_seq05_phase09_readiness_handoff_static() -> dict[str, Any]:
    """**G-P08-SEQ-05** — Phase 09 readiness checklist (static items green)."""
    errors: list[str] = []
    for item in build_synthesis_phase09_readiness_checklist_v1():
        if not item.get("passed"):
            errors.append(f"{item.get('checklist_id')}:{item.get('errors')}")
    return _seq_meta(GP08_SEQ05_GATE_ID_V1, "synthesis_phase09_readiness_handoff", errors)


def verify_gp08_seq06_wave_seven_complete_static() -> dict[str, Any]:
    """**G-P08-SEQ-06** — wave **7** deliverables (Steps **31–35**) wired."""
    errors: list[str] = []
    wave = evaluate_synthesis_implementation_wave_v1("7")
    if not wave.get("passed"):
        for d in wave.get("deliverables") or []:
            if not d.get("passed"):
                errors.append(f"{d.get('deliverable_id')}:{d.get('errors')}")
    return _seq_meta(GP08_SEQ06_GATE_ID_V1, "synthesis_wave_7_complete", errors)
