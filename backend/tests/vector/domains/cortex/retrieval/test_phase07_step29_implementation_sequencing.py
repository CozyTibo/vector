"""P07-29 — implementation sequencing (waves 0–5) + Phase 08 handoff."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.retrieval.retrieval_implementation_sequencing import (
    GP07_SEQ01_GATE_ID_V1,
    PHASE07_RETRIEVAL_IMPLEMENTATION_SEQUENCING_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_CRITICAL_PATH_MODULE_CHAIN_V1,
    RETRIEVAL_EVIDENCE_HIT_SCHEMA_LITERAL_V1,
    RETRIEVAL_IMPLEMENTATION_SEQUENCING_SPEC_REF_V1,
    RETRIEVAL_IMPLEMENTATION_WAVE_IDS_V1,
    RETRIEVAL_TRACKER_STEP_WAVE_RANGES_V1,
    build_retrieval_implementation_sequencing_catalog_v1,
    build_retrieval_phase08_readiness_checklist_v1,
    build_retrieval_tracker_step_wave_map_v1,
    evaluate_all_retrieval_implementation_waves_v1,
    evaluate_retrieval_implementation_wave_v1,
    verify_gp07_seq01_implementation_sequencing_catalog_static,
    verify_gp07_seq02_tracker_wave_mapping_static,
    verify_gp07_seq03_critical_path_modules_static,
    verify_gp07_seq04_waves_zero_through_five_complete_static,
    verify_gp07_seq05_phase08_readiness_handoff_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-implementation-sequencing-plan.md"
        if marker.is_file():
            return root
    msg = "repo root not found"
    raise RuntimeError(msg)


def test_constants_and_spec_ref() -> None:
    assert PHASE07_RETRIEVAL_IMPLEMENTATION_SEQUENCING_RUNTIME_SCHEMA_VERSION >= 1
    assert "phase-07-implementation-sequencing-plan" in RETRIEVAL_IMPLEMENTATION_SEQUENCING_SPEC_REF_V1
    assert RETRIEVAL_IMPLEMENTATION_WAVE_IDS_V1 == ("0", "1", "2", "3", "4", "5")
    assert len(RETRIEVAL_CRITICAL_PATH_MODULE_CHAIN_V1) == 10
    assert RETRIEVAL_EVIDENCE_HIT_SCHEMA_LITERAL_V1 == "RetrievalEvidenceHitV1"


def test_sequencing_doc_present() -> None:
    root = _repo_root()
    assert (root / "DOCS" / "cortex" / "retrieval" / "phase-07-implementation-sequencing-plan.md").is_file()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-implementation-sequencing-plan.md").read_text(
        encoding="utf-8"
    )
    assert "Wave 0" in text
    assert "anti_goals → query_contract" in text


def test_tracker_wave_map_covers_30_steps() -> None:
    rows = build_retrieval_tracker_step_wave_map_v1()
    assert len(rows) == 30
    assert int(rows[0]["tracker_step"]) == 1
    assert int(rows[-1]["tracker_step"]) == 30
    assert rows[0]["wave_label"] == RETRIEVAL_TRACKER_STEP_WAVE_RANGES_V1[0][2]


def test_all_seq_oracles_pass() -> None:
    assert verify_gp07_seq01_implementation_sequencing_catalog_static()["id"] == GP07_SEQ01_GATE_ID_V1
    assert verify_gp07_seq01_implementation_sequencing_catalog_static()["passed"] is True
    assert verify_gp07_seq02_tracker_wave_mapping_static()["passed"] is True
    assert verify_gp07_seq03_critical_path_modules_static()["passed"] is True
    assert verify_gp07_seq04_waves_zero_through_five_complete_static()["passed"] is True
    assert verify_gp07_seq05_phase08_readiness_handoff_static()["passed"] is True


def test_waves_zero_through_five_complete() -> None:
    for wid in RETRIEVAL_IMPLEMENTATION_WAVE_IDS_V1:
        wave = evaluate_retrieval_implementation_wave_v1(wid)
        assert wave["passed"] is True, wave
    assert evaluate_all_retrieval_implementation_waves_v1()["passed"] is True


def test_catalog_and_phase08_checklist() -> None:
    cat = build_retrieval_implementation_sequencing_catalog_v1()
    assert cat["all_waves_passed"] is True
    assert cat["phase08_readiness_passed"] is True
    assert len(cat["phase08_readiness_checklist"]) == 3
    p08 = build_retrieval_phase08_readiness_checklist_v1()
    assert all(item["passed"] for item in p08)
